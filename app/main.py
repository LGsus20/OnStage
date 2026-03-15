import os
import uvicorn
import asyncio
from datetime import timedelta
from typing import Annotated, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.music_retriever import download_video

from app.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.constants import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    ALGORITHM,
    ADMIN_USERNAME,
    ADMIN_PASSWORD_PLAIN,
    COOKIE_SECURE,
    MUSIC_FILES_DIR,
    SYNC_DEVIATION_SECONDS,
    RELOAD_SERVER
)
from jose import JWTError, jwt
from app.music_retriever import download_video
from app.state import music_state
from app.models import QueueItem, MoveQueueItem
from datetime import datetime, timezone
from app.state import music_state
from datetime import datetime, timezone

### Variables:
ADMIN_PASSWORD_HASHED = get_password_hash(ADMIN_PASSWORD_PLAIN)

# In-memory DB
users_db = {
    ADMIN_USERNAME: {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD_HASHED
    }
}


# Initialize FastAPI app
app = FastAPI(title="OnStage")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Dependencies ---

async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    
    # Allow any authenticated user session (no database check)
    return {"username": username}

async def get_current_user_required(user: Optional[dict] = Depends(get_current_user)):
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# --- Routes ---

@app.post("/download")
async def download_music(url: str = Form(...), user: dict = Depends(get_current_user_required)):
    # Basic validation for youtube URLs
    if "youtube.com" not in url and "youtu.be" not in url:
        return {"success": False, "message": "Invalid YouTube URL"}
    
    loop = asyncio.get_event_loop()
    # Pass username to download_video
    result = await loop.run_in_executor(None, download_video, url, user["username"], MUSIC_FILES_DIR)
    
    if result.get("success"):
        return {"success": True, "title": result.get("title"), "filename": result.get("filename")}
    else:
        return {"success": False, "message": result.get("error")}

@app.get("/music/{filename}")
async def get_music_file(filename: str, user: dict = Depends(get_current_user_required)):
    file_path = os.path.join(MUSIC_FILES_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/play")
async def play_music(filename: str = Form(...), user: dict = Depends(get_current_user_required)):
    file_path = os.path.join(MUSIC_FILES_DIR, filename)
    if not os.path.exists(file_path):
        return {"success": False, "message": "File not found"}
    
    music_state.current_song = filename
    music_state.start_time = datetime.now(timezone.utc)
    music_state.is_playing = True
    music_state.is_paused = False # reset pause state
    music_state.history.append({"filename": filename, "timestamp": music_state.start_time})
    
    return {"success": True, "current_song": filename}

@app.post("/pause")
async def pause_music(user: dict = Depends(get_current_user_required)):
    if not music_state.is_playing or music_state.is_paused:
        return {"success": False, "message": "Nothing playing or already paused"}
    
    music_state.is_paused = True
    music_state.pause_start_time = datetime.now(timezone.utc)
    return {"success": True, "message": "Music paused"}

@app.post("/resume")
async def resume_music(user: dict = Depends(get_current_user_required)):
    if not music_state.is_playing or not music_state.is_paused:
        return {"success": False, "message": "Nothing paused"}
    
    # Calculate how long we were paused
    now = datetime.now(timezone.utc)
    if music_state.pause_start_time:
        pause_duration = now - music_state.pause_start_time
        # Shift the start time forward by the pause duration
        # This makes it seem like the song started later, preserving the correct elapsed time
        if music_state.start_time:
            music_state.start_time += pause_duration
            
    music_state.is_paused = False
    music_state.pause_start_time = None
    
    return {"success": True, "message": "Music resumed"}

@app.get("/state")
async def get_state(user: dict = Depends(get_current_user_required)):
    state = {
        "current_song": music_state.current_song,
        "is_playing": music_state.is_playing,
        "is_paused": music_state.is_paused,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "sync_deviation": SYNC_DEVIATION_SECONDS,
        "queue": music_state.queue
    }
    
    if music_state.start_time:
        state["start_time"] = music_state.start_time.isoformat()
    else:
        state["start_time"] = None
        
    return state

@app.get("/queue")
async def get_queue(user: dict = Depends(get_current_user_required)):
    return {"queue": music_state.queue}

@app.post("/queue/add")
async def add_to_queue(item: QueueItem, user: dict = Depends(get_current_user_required)):
    file_path = os.path.join(MUSIC_FILES_DIR, item.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    queue_entry = {
        "filename": item.filename,
        "requested_by": user["username"]
    }
    
    if item.position is None:
        music_state.queue.append(queue_entry)
        msg = "Added to end of queue"
    else:
        # If queue is empty, handle 1-based index logically (1 is next up)
        # But list insert is 0-based.
        # User sees 1..N.
        # Python list expects 0..N-1
        # If user passes 1, insert at index 0. user passes 2, index 1.
        idx = max(0, item.position - 1)
        if idx > len(music_state.queue):
            music_state.queue.append(queue_entry)
        else:
            music_state.queue.insert(idx, queue_entry)
        msg = f"Added to position {idx + 1}"
        
    return {"success": True, "message": msg, "queue": music_state.queue}

@app.post("/queue/next")
async def play_next_song(user: dict = Depends(get_current_user_required), current_finished_song: Optional[str] = Form(None)):
    # Check if the song requesting to be skipped is actually the current one
    # This prevents multiple clients from skipping successive songs
    if current_finished_song and music_state.current_song != current_finished_song:
        return {"success": False, "message": "Song already changed"}

    if not music_state.queue:
        music_state.is_playing = False
        music_state.current_song = None
        music_state.start_time = None
        return {"success": True, "message": "Queue finished"}
    
    next_song = music_state.queue.pop(0)
    music_state.current_song = next_song["filename"]
    music_state.start_time = datetime.now(timezone.utc)
    music_state.is_playing = True
    music_state.is_paused = False # reset pause state
    music_state.history.append({"filename": music_state.current_song, "timestamp": music_state.start_time})
    
    return {"success": True, "current_song": music_state.current_song}

@app.post("/queue/move")
async def move_queue_item(request: MoveQueueItem, user: dict = Depends(get_current_user_required)):
    length = len(music_state.queue)
    if not (0 <= request.old_index < length):
        raise HTTPException(status_code=400, detail="Invalid old index")
    if not (0 <= request.new_index < length):
        raise HTTPException(status_code=400, detail="Invalid new index")

    item = music_state.queue.pop(request.old_index)
    music_state.queue.insert(request.new_index, item)

    return {"success": True, "message": "Queue updated", "queue": music_state.queue}

@app.delete("/queue/remove/{index}")
async def remove_item_from_queue(index: int, user: dict = Depends(get_current_user_required)):
    if index < 0 or index >= len(music_state.queue):
        raise HTTPException(status_code=400, detail="Invalid queue index")
        
    removed = music_state.queue.pop(index)
    return {"success": True, "message": f"Removed {removed['filename']}", "queue": music_state.queue}


@app.post("/queue/fair-shuffle")
async def fair_shuffle_queue(user: dict = Depends(get_current_user_required)):
    if not music_state.queue:
         return {"success": True, "message": "Queue is empty"}
         
    # Logic:
    # 1. Group songs by user, preserving the order users appeared in the queue.
    # 2. Reconstruct queue by taking 1 song from each user in a round-robin fashion.
    
    user_queues = {}
    users_order = [] # To keep track of the rotation order (First come, First Served basis of users)
    
    for item in music_state.queue:
        u = item["requested_by"]
        if u not in user_queues:
            user_queues[u] = []
            users_order.append(u)
        user_queues[u].append(item)
    
    new_queue = []
    
    # Iterate while we still have any songs left to pick
    while True:
        songs_picked_this_round = 0
        for u in users_order:
            if user_queues[u]:
                new_queue.append(user_queues[u].pop(0))
                songs_picked_this_round += 1
        
        if songs_picked_this_round == 0:
            break
            
    music_state.queue = new_queue
    return {"success": True, "message": "Queue shuffled fairly", "queue": music_state.queue}


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...)):
    # Authenticate using shared admin password
    if not verify_password(password, ADMIN_PASSWORD_HASHED):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Allow any username (sanitize simple check)
    if not username or len(username.strip()) < 1:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username required",
        )
    
    # Usernames must be ASCII compliant and alphanumeric (no hyphens, no weird characters)
    if not username.isascii() or not username.isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be alphanumeric ASCII characters only (a-z, A-Z, 0-9).",
        )

    # Use the provided username for the session
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,  
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, # Input in seconds, thus we multiply it by 60
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=COOKIE_SECURE
    )
    
    return {"msg": "Login successful", "access_token": access_token, "token_type": "bearer"}

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response

@app.get("/history/download")
async def download_history(user: dict = Depends(get_current_user_required)):
    # Get current time in UTC
    now = datetime.now(timezone.utc)
    twelve_hours_ago = now - timedelta(hours=12)
    
    # Filter history
    # music_state.history contains stored datetime objects. assuming they are timezone aware as we use timezone.utc
    recent_songs = []
    headers_line = f"Jam Session History - {now.strftime('%Y-%b-%d')}\n"
    content = [headers_line]
    content.append(f"Generated at: {now.strftime('%H:%M:%S UTC')}\n")
    content.append("=" * 50 + "\n\n")

    for item in music_state.history:
        ts = item.get("timestamp")
        # Ensure ts is timezone aware for comparison
        if ts and ts >= twelve_hours_ago:
            recent_songs.append(item)
    
    # Sort by time
    recent_songs.sort(key=lambda x: x.get("timestamp", datetime.min))
    
    for idx, item in enumerate(recent_songs, 1):
        time_str = item["timestamp"].strftime("%H:%M:%S")
        content.append(f"{idx}. [{time_str}] {item['filename']}\n")
        
    final_content = "".join(content)
    filename = f"Jam_list_{now.strftime('%Y-%b-%d')}.txt"
    
    return Response(
        content=final_content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: dict = Depends(get_current_user_required)):
    # List available music files
    music_files = []
    if os.path.exists(MUSIC_FILES_DIR):
        for f in os.listdir(MUSIC_FILES_DIR):
            if f.endswith(".mp3"):
                music_files.append(f)
    
    music_files.sort()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "username": user["username"],
        "music_files": music_files
    })

@app.get("/music/list")
async def get_music_list(response: Response, user: dict = Depends(get_current_user_required)):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    music_files = []
    if os.path.exists(MUSIC_FILES_DIR):
        for f in os.listdir(MUSIC_FILES_DIR):
            if f.endswith(".mp3"):
                music_files.append(f)
    music_files.sort()
    return {"files": music_files}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=RELOAD_SERVER)

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    file_path = "app/static/favicon.png"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return Response(status_code=404)

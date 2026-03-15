# OnStage - Admin Dashboard

A FastAPI application with secure login authentication.

## Security & Database
*   **Database**: Currently, this application uses an in-memory store for the single admin user. The password is injected via environment variables. It does not use SQLite or PostgreSQL.
*   **Auth**: Uses JWT tokens stored in HttpOnly cookies (XSS protection) and Bcrypt for password hashing.

## Setup Instructions (Ubuntu/Linux)

It is recommended to use a virtual environment (`.venv`) to avoid conflicts with system packages.

### 1. Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
pip install fastapi "uvicorn[standard]" python-multipart pyjwt passlib[bcrypt] jinja2
```

### 3. Run the Application
You can set your admin password before running. If you don't set it, the default is `admin`.

```bash
# Set your secure password
export ADMIN_PASSWORD="SuperSecretPassword123!"

# Run server
uvicorn app.main:app --reload
```

### 4. Access
Open [http://127.0.0.1:8000](http://127.0.0.1:8000)
*   **User**: `admin`
*   **Pass
```

## Security Notes

-   The login system uses JWT tokens stored in HTTP-only cookies to prevent XSS attacks.
-   Passwords are hashed using bcrypt.
-   The "admin" user is created at startup using the environment variables.

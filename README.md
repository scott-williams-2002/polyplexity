# PolyPlexity

PolyPlexity is an AI-powered chat interface that provides research capabilities and integrates with Polymarket prediction markets to offer relevant market recommendations based on user queries.

## Architecture

- **Frontend**: React + TypeScript application built with Vite
- **Backend**: FastAPI application with LangGraph agent for AI research and market analysis

## Prerequisites

### Frontend Prerequisites

- **Node.js** (v18 or higher recommended)
- **npm** (comes bundled with Node.js)
- **Vite** - The frontend uses Vite as the build tool. See [Vite documentation](https://vitejs.dev/guide/) for more information.

### Backend Prerequisites

- **Python** 3.8 or higher
- **pip** (Python package manager)

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. (Recommended) Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the polyplexity_agent package in editable mode:
   ```bash
   cd polyplexity_agent
   pip install -e .
   cd ..
   ```

4. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the backend server:
   ```bash
   python main.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn main:app --reload
   ```

   The backend will start on `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install frontend dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

   The frontend will start on `http://localhost:3000`

## Running the Application

1. **Start the backend server first** (in one terminal):
   ```bash
   cd backend
   python main.py
   ```

2. **Start the frontend development server** (in another terminal):
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access the application**:
   - Open your browser and navigate to `http://localhost:3000`
   - The frontend will communicate with the backend API at `http://localhost:8000`

## Environment Variables

The frontend uses environment variables for configuration. The default backend API URL is `http://localhost:8000`. You can override this by setting the `VITE_API_URL` environment variable.

## Development

- Frontend runs on port **3000** (configurable in `vite.config.ts`)
- Backend API runs on port **8000** (configurable in `main.py`)
- CORS is configured to allow requests from `http://localhost:3000`

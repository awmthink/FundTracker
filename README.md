# FundTracker

A lightweight and efficient fund investment management system that helps you track your mutual fund portfolio and visualize investment returns.

## Features

- **Transaction Management**
  - Record buy/sell transactions
  - Auto-calculate fees
  - Complete transaction history

- **Portfolio Analysis**
  - Real-time holdings overview
  - Dynamic return calculation
  - Auto NAV updates

- **Fee Management**
  - Flexible purchase fee settings
  - Multi-tier redemption fees
  - Quick fee template application

## Tech Stack

### Frontend
- Vue 3
- Element Plus
- Axios
- Vite

### Backend
- Python
- Flask
- SQLite
- Flask-CORS

## Getting Started

### Prerequisites
- Node.js >= 12.0.0
- Python >= 3.7
- pip package manager

### Installation

1. Clone the repository

```bash
git clone https://github.com/awmthink/FundTracker.git
cd FundTracker
```

2. Install frontend dependencies

```bash
cd frontend
npm install
```

3. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

4. Initialize database

```bash
python init_db.py
```

### Running the Application

1. Start backend server

```bash
cd backend
python app.py
```

2. Start frontend development server

```bash
cd frontend
npm run dev
```

3. Access the application at `http://localhost:5173`

## License

MIT License

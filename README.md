# SQL Explorer

A modern, feature-rich GUI application for SQL Server database management and exploration built with Python. SQL Explorer provides an intuitive interface for connecting to SQL Server instances, browsing databases, executing queries, visualizing database schemas, and building complex SQL joins.

---

## 📋 Table of Contents

- [Features](#-features)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Download & Setup](#-download--setup)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Technologies Used](#-technologies-used)
- [System Database Information](#-system-database-information)

---

## ✨ Features

### 🔌 Connection Management
- Connect to any SQL Server instance (local or remote)
- Support for both **Windows Authentication** and **SQL Server Authentication**
- Optional password saving with Base64 encoding
- Auto-connect on startup feature
- Real-time connection status indicator
- Session persistence (save connection details for later)

### 🗄️ Data Browser
- Browse all databases and tables in a hierarchical tree view
- Lazy-load database expansion for performance
- Quick table search and filtering
- View table data with configurable row limits (100, 500, 1000, 5000, or ALL)
- Display comprehensive column information (type, nullable, primary key, identity)
- Built-in search across all columns in the current table

### ✏️ Data Manipulation
- **Insert** new rows with field validation
- **Edit** existing rows (if table has primary key)
- **Delete** single or multiple rows with confirmation
- Real-time data refresh
- Smart field validation and error handling

### ⚙️ Query Runner
- Write and execute custom SQL queries
- Support for SELECT, INSERT, UPDATE, and DELETE operations
- Syntax highlighting with code editor
- Right-click context menu (Cut, Copy, Paste, Select All)
- F5 keyboard shortcut to execute queries
- Visual query results with sortable columns
- Detailed operation feedback (rows affected, execution status)
- Database selector for multi-database execution

### 🗺️ Entity Relationship Diagram (ERD) Visualizer
- Auto-generate interactive ERD for any selected database
- Visual representation of tables, columns, and relationships
- Primary key indicators (🔑)
- Identity column indicators (⚡)
- Foreign key relationship arrows (──▶)
- Pan and zoom controls
- Drag-to-pan and scroll-to-zoom interaction
- Zoom in/out buttons and reset functionality
- Legend with relationship indicators

### ⛓️ Join Builder
- Interactive visual join construction interface
- Support for multiple join types:
  - INNER JOIN
  - LEFT JOIN
  - RIGHT JOIN
  - FULL OUTER JOIN
  - CROSS JOIN
- Auto-detect foreign key relationships between tables
- Manual ON clause support for tables without FK relationships
- Configurable result row limits
- SQL preview before execution
- Send generated SQL to Query Runner for refinement

### 🎨 User Interface
- Modern dark theme (Catppuccin Mocha color palette)
- Responsive design with resizable windows
- Intuitive sidebar navigation
- Real-time status indicators
- Comprehensive logging in connection tab
- Modal dialogs for insert/edit operations
- Smooth scrollable frames and components

---

## 📋 Requirements

### System Requirements
- **Operating System**: Windows (with SQL Server driver support)
- **Python Version**: 3.8 or higher
- **SQL Server**: SQL Server 2012 or later
- **Minimum RAM**: 2GB
- **Minimum Screen Resolution**: 1100x700 pixels (optimal: 1450x860)

### Database Permissions
- Ability to connect to target SQL Server instance
- SELECT permissions on system tables (for schema exploration)
- Appropriate INSERT, UPDATE, DELETE permissions for data manipulation

---

## 🛠️ Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/OmarMohammmed2006/SQLApp.git
cd SQLApp
```

### Step 2: Create Virtual Environment (Optional but Recommended)

```bash
# For Windows
python -m venv venv
venv\Scripts\activate

# For Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

The following Python packages are required:

```bash
pip install customtkinter pyodbc
```

Or install from requirements.txt (if provided):

```bash
pip install -r requirements.txt
```

### Individual Package Installation

```bash
# CustomTkinter - Modern UI framework
pip install customtkinter

# PyODBC - SQL Server database driver
pip install pyodbc
```

### Step 4: Verify SQL Server ODBC Driver

Ensure you have the SQL Server ODBC driver installed:

```bash
# Windows PowerShell
Get-OdbcDriver -Name "SQL Server"

# If not installed, download from:
# https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
```

---

## 📥 Download & Setup

### Quick Start (No Virtual Environment)

1. **Download Repository**
   ```bash
   git clone https://github.com/OmarMohammmed2006/SQLApp.git
   cd SQLApp
   ```

2. **Install Dependencies**
   ```bash
   pip install customtkinter pyodbc
   ```

3. **Run Application**
   ```bash
   python main.py
   ```

### Full Setup with Virtual Environment

```bash
# 1. Clone the repository
git clone https://github.com/OmarMohammmed2006/SQLApp.git
cd SQLApp

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows
# or
source venv/bin/activate  # On Mac/Linux

# 3. Upgrade pip
pip install --upgrade pip

# 4. Install all dependencies
pip install customtkinter pyodbc

# 5. Launch the application
python main.py
```

### Docker Setup (Optional)

If Docker is available, you can containerize the application:

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install customtkinter pyodbc
CMD ["python", "main.py"]
```

---

## 🚀 Usage

### Starting the Application

```bash
python main.py
```

The application window will open with a welcome screen.

### Connection Tab (⚙️)

1. Enter your SQL Server details:
   - **Server/Instance**: `localhost`, `.\SQLEXPRESS`, or `SERVER\INSTANCE`
   - **Initial Database**: Leave blank to see all databases
   - **Authentication**: Choose "Windows Auth" or "SQL Server Auth"
   - **Username/Password**: Required for SQL Server Auth only

2. Optional settings:
   - ✓ **Save password**: Encrypts and saves credentials locally
   - ✓ **Auto-connect on startup**: Automatically connects on launch

3. Click **"Connect to SQL Server"** button
4. Monitor connection status in the log box

### Data Browser Tab (🗄️)

1. Expand database tree to view tables
2. Search tables using the filter box
3. Click a table to view its data
4. Adjust row limit if needed
5. Use action buttons:
   - **↻ Refresh**: Reload table data
   - **➕ Insert**: Add new rows
   - **✏ Edit**: Modify selected row
   - **🗑 Delete**: Remove rows
   - **ℹ Column Info**: View column metadata

### Query Runner Tab (▶️)

1. Select target database from dropdown
2. Write SQL query in the editor
3. Press **F5** or click **"▶ Run"** button
4. View results in the grid below
5. Results are sortable by clicking column headers

**Example Queries:**
```sql
SELECT TOP 100 * FROM YourTable
UPDATE YourTable SET ColumnName = 'Value' WHERE Condition
DELETE FROM YourTable WHERE ID = 5
INSERT INTO YourTable (Col1, Col2) VALUES ('Val1', 'Val2')
```

### Visualize Tab (🗺️)

1. Select database from dropdown
2. Click **"▶ Generate"** button
3. View interactive ERD:
   - **Drag** to pan around
   - **Scroll** to zoom in/out
   - Click **"＋ Zoom In"** / **"－ Zoom Out"** for fine control
   - Click **"↺ Reset"** to return to default view

**Legend:**
- 🔑 Primary Key columns
- ⚡ Identity/Auto-increment columns
- ──▶ Foreign key relationships

### Join Builder Tab (⛓️)

1. Select database
2. Choose left table
3. Choose join type (or use auto-detected)
4. Choose right table
5. Set row limit
6. Click **"⛓ Run Join"** button
7. View results
8. Click **"📋 Copy SQL to Query Runner"** to refine the query

**Join Types:**
- **INNER JOIN**: Only matching rows
- **LEFT JOIN**: All left table rows + matches
- **RIGHT JOIN**: All right table rows + matches
- **FULL OUTER JOIN**: All rows from both tables
- **CROSS JOIN**: Cartesian product (used when no FK exists)

---

## 📁 Project Structure

```
SQLApp/
├── main.py                 # Main application entry point
├── application.md          # Lab assignment documentation
├── inquiries.md           # Example SQL queries for reference
├── session.json           # Auto-saved connection settings (generated)
├── README.md              # This file
└── .idea/                 # IDE configuration (optional)
```

### Key Files

| File | Purpose |
|------|---------|
| `main.py` | Complete application with all GUI components and database logic |
| `application.md` | Original assignment details and specifications |
| `inquiries.md` | Example SQL queries for database testing |
| `session.json` | Persistent storage of connection credentials (encrypted) |

---

## 🛠️ Technologies Used

### Core Libraries
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.8+ | Programming language |
| **CustomTkinter** | Latest | Modern GUI framework with dark theme support |
| **PyODBC** | Latest | Database connectivity and query execution |
| **Tkinter** | Built-in | GUI framework (base for CustomTkinter) |

### Python Standard Libraries
- `json` - Configuration and session management
- `os` - File and path operations
- `datetime` - Timestamp logging
- `base64` - Password encryption
- `math` - ERD layout calculations

### External Dependencies

**CustomTkinter**
- Provides modern UI components
- Dark theme support (Catppuccin Mocha)
- Cross-platform compatibility

**PyODBC**
- SQL Server database connectivity
- Query execution
- Result fetching and transaction management

---

## 💾 System Database Information

SQL Server maintains several system databases that are automatically hidden from normal data operations:

| Database | Purpose |
|----------|---------|
| **master** | System metadata, logins, server-wide configuration |
| **tempdb** | Temporary tables and objects (recreated at restart) |
| **model** | Template for new databases |
| **msdb** | SQL Agent jobs, mail settings, backup info |

These databases appear in the browser with a 🔒 lock icon and should not be modified unless you have advanced SQL Server knowledge.

---

## ⚙️ Configuration

### Session File Format

`session.json` stores connection details:

```json
{
  "server": "localhost",
  "db": "YourDatabase",
  "auth": "windows",
  "user": "sa",
  "password": "base64encodedpassword",
  "save_pass": true,
  "auto_connect": false
}
```

**⚠️ Security Note**: Passwords are Base64-encoded (not truly encrypted). Do not share `session.json` files or commit them to version control.

### Color Theme (Catppuccin Mocha)

The application uses a carefully selected color palette:
- **Background**: `#1e1e2e`
- **Sidebar**: `#181825`
- **Accent**: `#cba6f7`
- **Text**: `#cdd6f4`
- **Success**: `#a6e3a1`
- **Error**: `#f38ba8`

---

## 🔍 Troubleshooting

### Connection Issues

**"ODBC driver not found"**
- Install SQL Server ODBC driver from Microsoft's official site
- Verify driver installation: `Get-OdbcDriver` (PowerShell)

**"Connection timed out"**
- Check SQL Server is running
- Verify firewall allows port 1433 (default SQL Server port)
- Confirm server name/IP is correct

**"Login failed"**
- Verify username and password
- Check user has database access permissions
- Ensure authentication mode matches server settings

### Data Display Issues

**"No tables appear in browser"**
- Verify you have SELECT permissions on system tables
- Check initial database selection
- Try clicking the refresh button (↻)

**"Sorting doesn't work"**
- Ensure you're sorting on the data view, not column info
- Check column data types are compatible

---

## 📊 Example Scenarios

### Scenario 1: Viewing Employee Data
```
1. Connection → Connect to HR database
2. Data Browser → Expand "dbo" → Select "Employees"
3. Set limit to 500 rows
4. Use search to find specific employee
5. Click ℹ Column Info to see data types
```

### Scenario 2: Creating a Report
```
1. Query Runner → Select database
2. Write complex SELECT with JOINs
3. Run query with F5
4. Results appear in grid
5. Copy SQL to file for documentation
```

### Scenario 3: Understanding Database Structure
```
1. Visualize → Select database
2. Generate ERD
3. Zoom and pan to explore relationships
4. Identify foreign keys and primary keys
5. Join Builder → Use identified relationships to build joins
```

---

## 🤝 Contributing

To contribute improvements or bug fixes:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/YourFeature`
3. Make your changes
4. Test thoroughly
5. Commit: `git commit -m 'Add YourFeature'`
6. Push: `git push origin feature/YourFeature`
7. Open a Pull Request

---

## 📝 License

This project is provided as-is for educational purposes. See repository for any additional licensing information.

---

## 👨‍💻 Author

**Omar Mohammmed** - [GitHub Profile](https://github.com/OmarMohammmed2006)

---

## 🆘 Support & Feedback

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Provide error messages and steps to reproduce

---

## 🎯 Future Enhancements

Potential features for future releases:
- [ ] Export data to CSV/Excel
- [ ] Query history and favorites
- [ ] Advanced filtering with SQL WHERE builder
- [ ] Multi-database comparisons
- [ ] Database backup/restore functionality
- [ ] Performance query analyzer
- [ ] Custom report generation
- [ ] Dark/Light theme toggle
- [ ] Stored procedures viewer and executor
- [ ] Transaction logging and rollback

---

## 📚 Resources

- [SQL Server Documentation](https://learn.microsoft.com/en-us/sql/sql-server/)
- [PyODBC Documentation](https://github.com/mkleehammer/pyodbc/wiki)
- [CustomTkinter Documentation](https://github.com/TomSchimansky/CustomTkinter)
- [SQL Tutorial](https://www.w3schools.com/sql/)

---

**Last Updated**: 2026-05-31  
**Python Version**: 3.8+  
**Status**: Active Development


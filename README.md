# 💊 Pharmacy Management System

A comprehensive web-based Pharmacy Management System built with **Streamlit** and **SQLite** that enables efficient management of drugs, customers, and orders.

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.0+-red.svg)
![SQLite](https://img.shields.io/badge/sqlite-3-green.svg)

---

## 📋 Table of Contents

- [Features](#features)
- [Technologies Used](#technologies-used)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Screenshots](#screenshots)
- [Database Schema](#database-schema)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

---

## ✨ Features

### 👤 Customer Features
- **User Registration & Authentication**: Secure signup and login system
- **Browse Medications**: View available drugs with images and pricing
- **Place Orders**: Add drugs to cart and place orders
- **Order History**: Track and view past orders
- **User Profile Management**: Update contact information

### 🔐 Admin Features
- **Drug Management**: Add, view, update, and delete drug inventory
- **Customer Management**: View, update, and delete customer accounts
- **Order Management**: View all customer orders
- **Inventory Tracking**: Monitor drug quantities and expiry dates
- **Dashboard Analytics**: Comprehensive overview of pharmacy operations

---

## 🛠️ Technologies Used

- **Frontend**: [Streamlit](https://streamlit.io/) - Interactive web framework
- **Backend**: Python 3.7+
- **Database**: SQLite3 - Lightweight relational database
- **Data Handling**: Pandas - Data manipulation and analysis
- **Image Processing**: Pillow (PIL) - Image handling

---

## 📦 Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Step-by-Step Guide

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/pharmacy-management-system.git
   cd pharmacy-management-system
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
   - **Windows**:
     ```bash
     .venv\Scripts\activate
     ```
   - **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```

4. **Install required dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**
   ```bash
   streamlit run main.py
   ```

6. **Access the application**
   - Open your browser and navigate to `http://localhost:8501`

---

## 🚀 Usage

### Admin Access
- **Username**: `admin`
- **Password**: `admin`

### Customer Access
1. Navigate to **SignUp** in the sidebar
2. Create a new account with your details
3. Login with your credentials to browse and order drugs

### Admin Dashboard
- **Drugs**: Manage drug inventory (Add/View/Update/Delete)
- **Customers**: Manage customer accounts (View/Update/Delete)
- **Orders**: View all customer orders
- **About**: Project information

---

## 📁 Project Structure

```
Pharmacy-Management-System/
│
├── main.py                 # Main application file
├── requirements.txt        # Python dependencies
├── drug_data.db           # SQLite database (auto-generated)
├── drugdatabase.sql       # Database schema
│
├── images/                # Drug images
│   ├── dolo650.jpg
│   ├── strepsils.JPG
│   └── vicks.JPG
│
├── .venv/                 # Virtual environment (not in repo)
└── .vscode/               # VS Code configuration
    └── launch.json
```

---

## 🗄️ Database Schema

### Customers Table
| Column | Type | Description |
|--------|------|-------------|
| C_Name | VARCHAR(50) | Customer name |
| C_Password | VARCHAR(50) | Customer password |
| C_Email | VARCHAR(50) | Email (Primary Key) |
| C_State | VARCHAR(50) | State/Area |
| C_Number | VARCHAR(50) | Phone number |

### Drugs Table
| Column | Type | Description |
|--------|------|-------------|
| D_Name | VARCHAR(50) | Drug name |
| D_ExpDate | DATE | Expiry date |
| D_Use | VARCHAR(50) | Usage/Purpose |
| D_Qty | INT | Quantity available |
| D_id | INT | Drug ID (Primary Key) |

### Orders Table
| Column | Type | Description |
|--------|------|-------------|
| O_Name | VARCHAR(100) | Customer name |
| O_Items | VARCHAR(100) | Ordered items |
| O_Qty | VARCHAR(100) | Quantities |
| O_id | VARCHAR(100) | Order ID (Primary Key) |

---

## 🔮 Future Enhancements

- [ ] Payment gateway integration
- [ ] Email notifications for orders
- [ ] Prescription upload feature
- [ ] Advanced search and filtering
- [ ] Sales analytics and reporting
- [ ] Mobile responsive design
- [ ] Multi-language support
- [ ] Automated inventory alerts
- [ ] PDF invoice generation

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

---

## 👨‍💻 Author

**Himanshu Sharma**

- Email: himanshu.sharma3100@gmail.com

---

## 🙏 Acknowledgments

- Built as a mini project for learning purposes
- Special thanks to the Streamlit community for excellent documentation
- Icons and badges from [Shields.io](https://shields.io/)

---

## ⚠️ Disclaimer

This is an educational project and should not be used in production environments without proper security enhancements and medical compliance checks.

---

<div align="center">
Made with ❤️ by Himanshu Sharma
</div>

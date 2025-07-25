🚖 Swift Ride – A Smart Ride-Hailing App with Bargaining System
<p align="center"> <img src="https://img.shields.io/badge/Flutter-Mobile-blue?logo=flutter" /> <img src="https://img.shields.io/badge/Django-Backend-green?logo=django" /> <img src="https://img.shields.io/badge/PostgreSQL-Database-blue?logo=postgresql" /> <img src="https://img.shields.io/badge/Redis-Cache-red?logo=redis" /> <img src="https://img.shields.io/badge/License-MIT-lightgrey?logo=opensourceinitiative" /> </p>
🚀 Overview
Swift Ride is an innovative ride-hailing platform that introduces a bargaining system—riders can propose prices and drivers can accept or counter them. The app supports real-time communication, emergency features, and multilingual support across multiple platforms and user roles.

🛠️ Technology Stack
🔧 Backend
Framework: Django + Django REST Framework

Database: PostgreSQL

Caching: Redis

Async Tasks: Celery

Real-time: Django Channels (WebSockets)

📱 Frontend
Mobile App: Flutter (iOS & Android)

Admin Panel: React + TypeScript

State Management: BLoC (Flutter), Redux Toolkit (React)

🌐 Services
Maps: Google Maps SDK

Auth: Firebase Auth / Custom OTP

Payments: Paystack, Flutterwave, Stripe

Notifications: Firebase Cloud Messaging (FCM)

Voice Commands: Google Speech-to-Text

SMS: Twilio

🏗️ System Architecture
scss
Copy
Edit
┌───────────────────┐    ┌────────────────────┐
│   Flutter App     │    │  React Admin Panel │
│ (Riders & Drivers)│    │                    │
└────────┬──────────┘    └──────────┬─────────┘
         │                          │
         └──────────────┬───────────┘
                        │
           ┌────────────▼────────────┐
           │      Django Backend     │
           │  (REST API + WebSocket)│
           └────────────┬───────────┘
                        │
           ┌────────────▼────────────┐
           │      PostgreSQL DB      │
           └─────────────────────────┘
📈 Project Status
✅ Completed
Project structure design

Tech stack selection

Architecture planning

🚧 In Progress
Backend setup & config

Database schema design

Flutter app initialization

🗓️ Upcoming
OTP Authentication

Core ride & bargain features

WebSocket integration

Payment workflows

📦 Getting Started
⚙️ Prerequisites
Python 3.9+

Flutter SDK 3.0+

Node.js 16+

PostgreSQL 13+

Redis 6+

🚀 Backend Setup
bash
Copy
Edit
# Clone repo
git clone https://github.com/levah147/swift_ride_backend.git
cd swift-ride/swift_ride_backend

# Setup virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements/development.txt

# Database setup
python manage.py migrate
python manage.py createsuperuser

# Start development server
python manage.py runserver
📱 Flutter App Setup
bash
Copy
Edit
cd swift_ride_flutter
flutter pub get
flutter run
🖥️ Admin Panel Setup
bash
Copy
Edit
cd swift_ride_admin
npm install
npm start
📲 Features
💡 Core
🔐 OTP-based phone auth

🗺️ Live location tracking

💬 In-app chat & voice notes

💸 Real-time price negotiation

🌍 Multi-language support

🆘 Emergency panic button

🌟 Driver preferences

🚀 Advanced
🎙️ Voice-based ride requests

🚺 Women-only ride mode

🌿 Eco-friendly vehicle options

🔒 Secure pickup phrase

📱 Offline booking via SMS

🎁 Referral & loyalty programs

🤖 AI-powered fare suggestions

👥 User Roles
👤 Riders
Ride booking with price offer

Driver chat & reviews

Favorite drivers

SOS button

🚘 Drivers
Accept or counter offers

Real-time navigation

Vehicle management

Earnings dashboard

🛠️ Admins
Manage users & rides

Respond to emergencies

Monitor analytics

Configure system settings

📚 API Documentation
Available at: /api/docs/ (when dev server is running)

🧪 Testing
🔍 Backend
bash
Copy
Edit
cd swift_ride_backend
python manage.py test
📱 Flutter
bash
Copy
Edit
cd swift_ride_flutter
flutter test
🖥️ Admin Panel
bash
Copy
Edit
cd swift_ride_admin
npm test
📊 Project Management
Tasks: GitHub Issues

Docs: GitHub Wiki

CI/CD: GitHub Actions

Hosting: AWS / DigitalOcean

🤝 Contributing
Fork the repo

Create a feature branch

Make your changes

Add or update tests

Open a pull request

📄 License
This project is licensed under the MIT License. See the LICENSE file for details.

📞 Support
For questions or support:

📧 Email: support@swiftride.com

📘 Docs: docs.swiftride.com

🗺️ Roadmap
Check the ROADMAP.md for planned features and updates.
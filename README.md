# FilingDeck — Compliance & Tax Services

FilingDeck is a complete Flask-based web application designed to offer MSMEs, startups, and freelancers affordable tax and compliance filing services. It includes a smart compliance engine that calculates and visually plots upcoming deadlines on an interactive calendar.

## 🚀 Features

- **Compliance Engine (`compliance.py`)**: Computes filing deadlines (GST, TDS, Income Tax) over a rolling 6-month window based on business type and registration rules.
- **Interactive Visual Calendar**: A dynamically rendered JavaScript grid showing safe, upcoming, urgent, and critical deadlines.
- **Dedicated Service Pages**: SEO-optimized, dynamic detail pages for all major services (GST, ITR, etc.) with process timelines and penalty warnings.
- **AI Chatbot (`chatbot.py`)**: Integrated Google Gemini AI to instantly answer client compliance questions directly on the website.
- **Twilio WhatsApp Bot**: Automated server-side webhook that replies to WhatsApp messages with a professional greeting and links.
- **Security & CI/CD**: Automated GitHub Actions workflow using `vulnledger` to block vulnerable packages from production.
- **Serverless Ready**: Configured via `vercel.json` and a clean `requirements.txt` for instant, free deployment on Vercel.

## 💻 Tech Stack

- **Backend**: Python 3.10+, Flask, Flask-SQLAlchemy
- **AI & Integrations**: Google Gemini AI API, Twilio Messaging API
- **Database**: SQLite (routes to `/tmp` in serverless environments)
- **Frontend**: HTML5, Jinja2, Vanilla CSS (Glassmorphism design), Vanilla JS
- **Deployment & CI**: Vercel Serverless Functions, GitHub Actions

## ⚙️ Installation and Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/KavyaKajavadra/FilingDeck.git
   cd FilingDeck
   ```

2. **Set up Environment Variables**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your-secret-key
   GEMINI_API_KEY=your-google-gemini-key
   TWILIO_ACCOUNT_SID=your-twilio-sid
   TWILIO_AUTH_TOKEN=your-twilio-token
   ```

3. **Create a virtual environment & Install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```
   Navigate to `http://127.0.0.1:5000`

## 🚀 Deployment (Vercel)

FilingDeck is optimized for free Serverless hosting on Vercel:
1. Import the repository into your Vercel dashboard.
2. Add the environment variables from your `.env` file into the Vercel Settings.
3. Click **Deploy**. Vercel will automatically read `vercel.json`, install dependencies, and launch the site.

## 📂 Project Structure

```text
FilingDeck/
├── app.py                 # Flask server, Twilio webhooks, routes, and DB models
├── compliance.py          # Deadline calculation engine for GST, TDS, etc.
├── chatbot.py             # Google Gemini AI integrations
├── requirements.txt       # Clean dependency list
├── vercel.json            # Vercel Serverless Function config
├── .github/workflows/     # GitHub Actions (Security pipeline)
├── static/
│   ├── css/
│   │   └── main.css       # Core design system and styles
│   └── js/
│       ├── animations.js  # Scroll reveal and frontend micro-animations
│       └── calendar.js    # Logic for rendering the interactive visual calendar
└── templates/             # Jinja2 HTML templates
    ├── base.html
    ├── index.html
    ├── services.html
    ├── service_detail.html
    ├── about.html
    ├── contact.html
    └── calendar_results.html
```

## Contributing
Contributions are welcome. Please open an issue or submit a pull request for any enhancements or bug fixes.

## 👥 Meet the Team
- **Kavya Kajavadra** — Tech Lead & Web Developer
- **Parth Mehta** — Tax & Compliance (CA Finalist)
- **Yug Jain** — Tax Advisory (CA Aspirant)
- **Deep Patel** — Accounting Operations (BAF)
- **Nilkanth Saliya** — Financial Planning (BFM)
- **Bhavyy Jain** — Legal & Compliance Advisory (CS Executive)

Built with 💙 for MSMEs and Freelancers in India.

## License
This project is licensed under the MIT License.

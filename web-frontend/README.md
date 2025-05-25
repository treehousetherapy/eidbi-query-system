# EIDBI Chat UI - Modern Web Frontend

A modern, ChatGPT-style chat interface for the Ask EIDBI Assistant built with HTML, Tailwind CSS, and vanilla JavaScript.

## Features

- **ChatGPT-like Interface**: Clean, dark theme with rounded chat bubbles
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Chat**: Typing indicators and smooth animations
- **Message History**: Persists chat history in local storage
- **Modern Styling**: Uses Tailwind CSS and Inter font
- **API Integration**: Connects to the EIDBI backend service

## Design Elements

- **Color Scheme**: Dark gray background (#111827) with lighter gray cards (#1F2937)
- **User Messages**: Right-aligned, green background (#059669)
- **Assistant Messages**: Left-aligned, dark gray background (#374151)
- **Animations**: Fade-in and slide-up effects for new messages
- **Typography**: Inter font family for modern, clean text

## Running Locally

1. Start the backend service (see main README)

2. Run the web server:
   ```bash
   cd web-frontend
   python server.py
   ```

3. Open your browser to `http://localhost:8080`

## File Structure

```
web-frontend/
├── index.html      # Main HTML file with Tailwind CSS
├── js/
│   └── chat.js     # Chat functionality and API integration
├── css/            # (Reserved for custom CSS if needed)
├── assets/         # (Reserved for images/icons if needed)
├── server.py       # Simple Python HTTP server
└── README.md       # This file
```

## Customization

### Changing Colors

The color scheme uses Tailwind's color palette. To change:
- User messages: Change `bg-green-600` classes
- Assistant messages: Change `bg-gray-700` classes
- Background: Change `bg-gray-900` and `bg-gray-800` classes

### API Configuration

Edit the `API_URL` constant in `js/chat.js` to point to your backend:
```javascript
const API_URL = 'https://your-backend-url.com';
```

## Browser Support

- Chrome (recommended)
- Firefox
- Safari
- Edge

## Dependencies

- **Tailwind CSS**: Loaded via CDN
- **Inter Font**: Loaded from Google Fonts
- No JavaScript framework required (vanilla JS)

## Security

- XSS protection with HTML escaping
- CORS configured for API calls
- No sensitive data stored locally 
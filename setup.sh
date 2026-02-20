#!/bin/bash

# Busy WhatsApp Gateway Setup Script
# Run this script after cloning the repository

echo "==============================================="
echo "Busy WhatsApp Gateway - Setup"
echo "==============================================="
echo ""

# Check Python version
echo "Checking Python installation..."
python --version

if [ $? -ne 0 ]; then
    echo "ERROR: Python not found. Please install Python 3.9+ (32-bit recommended)"
    exit 1
fi

echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo ""
echo "Creating environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ Created .env file from template"
    echo "⚠ Please edit .env with your configuration"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "==============================================="
echo "Setup Complete!"
echo "==============================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration:"
echo "   - BDS_FILE_PATH: Path to your Busy .bds file"
echo "   - WHATSAPP_PROVIDER: meta/webhook (baileys coming soon)"
echo "   - Meta Business API credentials"
echo ""
echo "2. Start the server:"
echo "   ./start-server.bat (Windows)"
echo "   python -m uvicorn app.main:app --reload (Linux/Mac)"
echo ""
echo "3. Test the API:"
echo "   ./run-tests.bat (Windows)"
echo "   python tests/test_webhook.py (Linux/Mac)"
echo ""
echo "4. Configure Busy SMS URL:"
echo "   http://YOUR_IP:8000/api/v1/send-invoice?phone={MobileNo}\&msg={Message}\&pdf_url={AttachmentURL}"
echo ""

# Getting WhatsApp Cloud API Production Token

## Current Status
You're using a **User Access Token** (expires in ~60 days).

## For Production: Use System Token

### Option A: Never-Expiring Token (Recommended)

1. Go to: https://developers.facebook.com/tools/explorer/
2. Select your app: "Anjali Home Fashion"
3. Get User Token with permissions:
   - `whatsapp_business_management`
   - `whatsapp_business_messaging`
   - `business_management`
4. Convert to Long-Lived Token:
   ```bash
   curl -i -X GET "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
   ```
5. Then get Permanent Page Token (optional but best)

### Option B: App Dashboard (Easiest)

1. Go to: https://developers.facebook.com/apps/YOUR_APP_ID/whatsapp-business/settings/
2. Under "System Users" → Create System User
3. Assign WhatsApp Business Account
4. Generate Token with permissions:
   - `whatsapp_business_management`
   - `whatsapp_business_messaging`

### Required Permissions:
- `whatsapp_business_management` - Manage templates, phone numbers
- `whatsapp_business_messaging` - Send/receive messages

## To Update .env:

Replace:
```
META_ACCESS_TOKEN=EAALQ1Vpkxr0...
```

With your new permanent token.

## Security Best Practices:

1. **Never commit .env to git** (already in .gitignore ✓)
2. **Rotate tokens** every 90 days
3. **Use environment variables** in production servers
4. **Limit token permissions** to only what's needed

## Testing Token Validity:

```bash
curl -X GET "https://graph.facebook.com/v19.0/me?fields=id,name" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

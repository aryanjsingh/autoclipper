# Guide to Bilibili Login Alternatives

## Problem Background

Scanning the QR code to log in can easily trigger Bilibili's risk control mechanism, resulting in login failure or account restrictions. To resolve this issue, we offer several alternative login methods.

## Supported Login Methods

### 1. Cookie Import Login ⭐⭐⭐⭐⭐ (Recommended)

**Advantages:**
- Will not trigger Bilibili risk control
- High login success rate
- Easy to operate
- Good security (local encrypted storage)

**Disadvantages:**
- Requires manual cookie acquisition
- Cookies are time-sensitive and need to be updated regularly

**Applicable Scenarios:**
- Daily use
- Batch account management
- Avoiding risk control requirements

**How to Use:**
1. Log in to Bilibili in the browser
2. Press F12 to open developer tools
3. Switch to the Network tab
4. Refresh the page and find any request
5. Copy the value of the Cookie field in the request header
6. Paste into AutoClip's Cookie input box

### 2. Account and Password Login ⭐⭐⭐

**Advantages:**
- Intuitive operation
- No additional tools required

**Disadvantages:**
- May require verification code handling
- Risk of triggering risk control
- Requires sensitive information

**Applicable Scenarios:**
- New user first login
- Unable to obtain cookies

**How to Use:**
1. Enter Bilibili username or phone number
2. Enter password
3. Set nickname
4. Click to log in

### 3. QR Code Scan Login ⭐⭐

**Advantages:**
- Easy to operate
- No password required

**Disadvantages:**
- Easily triggers Bilibili risk control
- Lower success rate
- Requires Bilibili mobile app

**Applicable Scenarios:**
- Temporary testing
- When other methods are unavailable

**How to Use:**
1. Click "Start QR code scan login"
2. Use the Bilibili app to scan the QR code
3. Confirm login in the app

### 4. Third-Party Login ⭐⭐

**Advantages:**
- No Bilibili account and password required
- Relatively safe

**Disadvantages:**
- Requires third-party account
- Complex process
- Limited support

**Applicable Scenarios:**
- Users with WeChat or QQ accounts
- When you prefer not to use Bilibili account and password

## Recommended Strategies

### Recommended for Daily Use

1. **Preferred: Cookie Import**
   - The most stable and reliable method
   - Will not trigger risk control
   - Recommended to update cookies regularly

2. **Alternative: Account and Password Login**
   - Use when cookies expire
   - Pay attention to verification code handling

### Batch Account Management
- Uniformly use cookie import method
- Establish a cookie update mechanism
- Check account status regularly

### New User Guidance
1. Provide detailed tutorials on obtaining cookies
2. Create a visual how-to guide
3. Provide one-click copy functionality

## Safety Precautions

### Cookie Security
- Cookies contain login credentials; keep them safe
- Do not share with others
- Change cookies regularly
- Clean up promptly after use

### Account Security
- Do not log in on public devices
- Check account status regularly
- Handle exceptions in a timely manner

## Technical Implementation

### Backend API

```python
# Cookie verification
async def validate_bilibili_cookies(cookies: dict) -> dict:
    """Verify Bilibili cookie validity"""
    # Use cookies to access user info API
    # Return validation result and user information

# Account and password login
async def bilibili_password_login(username: str, password: str) -> dict:
    """Bilibili account and password login"""
    # Handle verification codes and login flow
    # Return login result
```

### Frontend Components

```typescript
// Support for multiple login methods
const loginMethods = [
  { id: 'cookie', name: 'Cookie Import', recommended: true },
  { id: 'password', name: 'Account & Password', recommended: true },
  { id: 'qr', name: 'QR Code Login', recommended: false },
  { id: 'wechat', name: 'WeChat Login', recommended: false },
  { id: 'qq', name: 'QQ Login', recommended: false }
]
```

## Troubleshooting

### FAQ

1. **Invalid Cookie**
   - Check if the cookie has expired
   - Confirm the cookie format is correct
   - Obtain cookies again

2. **Account and Password Login Failed**
   - Check whether the username and password are correct
   - Confirm whether a verification code is required
   - Try using cookie import

3. **QR Code Login Timeout**
   - Check network connection
   - Confirm Bilibili app version
   - Try another login method

### Debugging Methods
1. View browser console error messages
2. Check network request status
3. View backend logs
4. Analyze using developer tools

## Changelog

### v1.0.0
- Added cookie import login
- Added account and password login
- Optimized QR code login flow
- Added login method selection interface

### Follow-up Plan
- Add automatic cookie update functionality
- Support more third-party logins
- Optimize user experience
- Enhance security

## Related Documents

- [Cookie Acquisition Detailed Tutorial](./COOKIE_GETTING_GUIDE.md)
- [Bilibili API Interface Documentation](./BILIBILI_API_DOCS.md)
- [Security Best Practices](./SECURITY_BEST_PRACTICES.md)

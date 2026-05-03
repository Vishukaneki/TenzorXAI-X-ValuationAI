# Image Analysis Setup

The image analysis feature uses Cloudflare Workers AI to analyze property images. Here's how to set it up:

## Option 1: Using Cloudflare Workers AI (Recommended)

1. **Get Cloudflare Credentials:**
   - Sign up for a Cloudflare account at [cloudflare.com](https://www.cloudflare.com/)
   - Find your Account ID in the Cloudflare dashboard
   - Generate an API Token with Workers AI permissions

2. **Configure Environment Variables:**
   Edit `backend/.env` and fill in your credentials:
   ```env
   # Cloudflare Workers AI Credentials
   CF_ACCOUNT_ID=your_account_id_here
   CF_API_TOKEN=your_api_token_here
   
   # Set to true to enable mock image analysis (for testing without Cloudflare)
   MOCK_IMAGE_ANALYSIS=false
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

## Option 2: Using Mock Analysis (For Testing)

If you want to test the image analysis feature without Cloudflare:

1. **Enable Mock Analysis:**
   Edit `backend/.env`:
   ```env
   # Cloudflare Workers AI Credentials
   CF_ACCOUNT_ID=
   CF_API_TOKEN=
   
   # Set to true to enable mock image analysis (for testing without Cloudflare)
   MOCK_IMAGE_ANALYSIS=true
   ```

2. **No Additional Setup Required:**
   The system will automatically use mock responses when `MOCK_IMAGE_ANALYSIS=true`.

## How It Works

1. Users can upload property images through the frontend form
2. Images are sent to the `/valuate-with-image` endpoint
3. The backend sends images to Cloudflare Workers AI (LLaVA model)
4. AI analysis results are incorporated into risk flags and confidence scoring
5. Results are displayed in the frontend valuation report

## Testing

To test the image analysis feature:

1. Start the backend server:
   ```bash
   python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```

2. Use the frontend form to upload an image
3. Check the valuation results for image-based risk flags and confidence scores
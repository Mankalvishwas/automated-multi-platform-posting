from app.config import settings

print("Application:", settings.APP_NAME)
print("Version:", settings.APP_VERSION)
print("Gemini Model:", settings.GEMINI_MODEL)

if settings.GEMINI_API_KEY:
    print("Gemini API Key: Configured")
else:
    print("Gemini API Key: Missing")
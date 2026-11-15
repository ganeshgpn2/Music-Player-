# Music Player (Audio/Video, Offline + YouTube)

## सुविधाहरू
- फोनका गीत/भिडियो (Offline), Background play, Notification controls
- Back/Forward/Play/Pause/Stop, Seekbar, Speed
- Repeat One / Repeat All / No Repeat, Shuffle (Random), Serial
- Sleep timer, Playlist, Favorites (मनपर्ने), इतिहास, धेरै बजेको, नबजेको
- Home screen widget 4x1 र 4x2
- YouTube खोज र एपभित्रै play (Online)

## APK बनाउने तरिका
1. Android Studio मा यो फोल्डर Open गर्नुहोस्, Gradle sync हुन दिनुहोस्।
2. console.cloud.google.com → "YouTube Data API v3" Enable → API key बनाउनुहोस्।
3. `local.properties` मा थप्नुहोस्: YOUTUBE_API_KEY=तपाईंको_key
4. Build → Build APK(s) → app/build/outputs/apk/debug/app-debug.apk

## Widget राख्ने
Home screen लामो थिच्नुहोस् → Widgets → "Music Player 4x1" वा "4x2"।

## GitHub बाट APK बनाउने
1. GitHub मा नयाँ repository बनाउनुहोस्, र यो फोल्डरका सबै फाइल (.github सहित) upload गर्नुहोस्।
2. Repo → Settings → Secrets and variables → Actions → New repository secret
   नाम: YOUTUBE_API_KEY, मान: तपाईंको key
3. Actions ट्याब → "Build APK" → Run workflow (वा फाइल push गर्दा आफैं चल्छ)।
4. हरियो ✔ आएपछि run खोल्नुहोस् → तल Artifacts → MusicPlayer-APK डाउनलोड गर्नुहोस् (zip भित्र app-debug.apk)।

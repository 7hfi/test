# Sanrio Motion

A cute Sanrio-themed motion design & video effects editor built with Flutter, inspired by Alight Motion and After Effects.

## Features (MVP)

* Import videos from device gallery.
* Trim and crop clips via intuitive timeline.
* Pick output frame-rate (24 fps → 60 fps).
* Sanrio pastel UI with Comic Neue font.
* Smooth keyframe curve preview (proof-of-concept).
* Export edited video with FFmpeg and automatically save it back to the camera roll (iOS / Android Gallery).

> This is a lightweight prototype showcasing core flow; many advanced AE-like features can be layered on top.

## Getting started

1. Install Flutter ≥ 3.10 and enable iOS / Android tooling.
2. Fetch packages:

```bash
flutter pub get
```

3. Run on device or simulator:

```bash
flutter run
```

### iOS notes
* Add usage strings to `ios/Runner/Info.plist`:
  * `NSPhotoLibraryUsageDescription`
  * `NSCameraUsageDescription`
* Enable background audio for FFmpeg if desired.

### Android notes
* Update `android/app/src/main/AndroidManifest.xml` to include storage permissions.
* For Android 13+, add `READ_MEDIA_VIDEO` permission.

## Assets & Fonts
The project references the **Comic Neue** Google Font and expects Sanrio-style images under `assets/images/`. Feel free to add your own PNGs/SVGs.

---
Made with 💖 by Cursor & ChatGPT

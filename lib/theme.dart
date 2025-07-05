import 'package:flutter/material.dart';

ThemeData sanrioTheme() {
  const pink = Color(0xFFFFC1CC);
  const mint = Color(0xFFA8E6CF);
  const yellow = Color(0xFFFFF4B7);
  const lavender = Color(0xFFE0BBFF);

  final textTheme = Typography.blackCupertino.copyWith(
    bodySmall: const TextStyle(fontFamily: 'Comic Neue'),
    bodyMedium: const TextStyle(fontFamily: 'Comic Neue'),
    bodyLarge: const TextStyle(fontFamily: 'Comic Neue'),
    titleMedium: const TextStyle(fontFamily: 'Comic Neue', fontWeight: FontWeight.bold),
  );

  return ThemeData(
    primaryColor: pink,
    colorScheme: ColorScheme.light(
      primary: pink,
      secondary: mint,
      surface: Colors.white,
      background: yellow,
      onPrimary: Colors.white,
      onSecondary: Colors.white,
      onSurface: Colors.black,
      onBackground: Colors.black,
      error: Colors.red.shade400,
      onError: Colors.white,
    ),
    textTheme: textTheme,
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        foregroundColor: Colors.white,
        backgroundColor: pink,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        textStyle: const TextStyle(
          fontFamily: 'Comic Neue',
          fontWeight: FontWeight.bold,
        ),
      ),
    ),
    appBarTheme: const AppBarTheme(
      elevation: 0,
      backgroundColor: pink,
      foregroundColor: Colors.white,
    ),
  );
}
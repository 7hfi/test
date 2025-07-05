import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/home_screen.dart';
import 'theme.dart';
import 'video_editor_state.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const SanrioMotionApp());
}

class SanrioMotionApp extends StatelessWidget {
  const SanrioMotionApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => VideoEditorState(),
      child: MaterialApp(
        title: 'Sanrio Motion',
        debugShowCheckedModeBanner: false,
        theme: sanrioTheme(),
        home: const HomeScreen(),
      ),
    );
  }
}
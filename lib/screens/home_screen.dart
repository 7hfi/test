import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../video_editor_state.dart';
import 'editor_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final videoState = context.watch<VideoEditorState>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Sanrio Motion'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            ElevatedButton.icon(
              icon: const Icon(Icons.add),
              label: const Text('New Project'),
              onPressed: () async {
                await videoState.pickVideo();
                if (videoState.videoFile != null) {
                  // ignore: use_build_context_synchronously
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => const EditorScreen(),
                    ),
                  );
                }
              },
            ),
            const SizedBox(height: 20),
            const Text(
              'Create cute edits with Sanrio vibes! ^_^',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }
}
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:video_editor/video_editor.dart';
import 'package:fl_chart/fl_chart.dart';
import '../widgets/keyframe_graph_widget.dart';

import '../video_editor_state.dart';

class EditorScreen extends StatefulWidget {
  const EditorScreen({super.key});

  @override
  State<EditorScreen> createState() => _EditorScreenState();
}

class _EditorScreenState extends State<EditorScreen> {
  int? _selectedFps;

  final List<int> _fpsOptions = [24, 25, 30, 48, 60];
  final List<FlSpot> _demoCurve = const [
    FlSpot(0, 0),
    FlSpot(0.3, 0.1),
    FlSpot(0.6, 0.9),
    FlSpot(1, 1),
  ];

  @override
  Widget build(BuildContext context) {
    final videoState = context.watch<VideoEditorState>();
    final controller = videoState.controller;

    if (controller == null || !controller.initialized) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Editor'),
        actions: [
          IconButton(
            onPressed: videoState.isExporting
                ? null
                : () {
                    videoState.exportVideo(fps: _selectedFps);
                  },
            icon: const Icon(Icons.save),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: VideoViewer(controller: controller),
          ),
          Container(
            color: Theme.of(context).colorScheme.secondary.withOpacity(0.2),
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    const Text('FPS:'),
                    const SizedBox(width: 8),
                    DropdownButton<int>(
                      value: _selectedFps,
                      hint: const Text('Auto'),
                      items: _fpsOptions
                          .map((fps) => DropdownMenuItem(
                                value: fps,
                                child: Text('$fps fps'),
                              ))
                          .toList(),
                      onChanged: (v) {
                        setState(() {
                          _selectedFps = v;
                        });
                      },
                    ),
                    const Spacer(),
                    if (videoState.isExporting)
                      Expanded(
                        child: LinearProgressIndicator(
                          value: videoState.exportProgress,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 8),
                TrimSlider(
                  controller: controller,
                  viewerHeight: 50,
                  viewerWidth: MediaQuery.of(context).size.width,
                ),
                const SizedBox(height: 8),
                ElevatedButton(
                  onPressed: () {
                    showDialog(
                        context: context,
                        builder: (context) => AlertDialog(
                              title: const Text('Keyframe Graph'),
                              content: SizedBox(
                                  width: 300,
                                  child: KeyframeGraphWidget(points: _demoCurve)),
                              actions: [
                                TextButton(
                                    onPressed: () => Navigator.of(context).pop(),
                                    child: const Text('Close')),
                              ],
                            ));
                  },
                  child: const Text('Show Graph'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
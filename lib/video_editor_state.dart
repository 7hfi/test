import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:video_editor/video_editor.dart';
import 'package:ffmpeg_kit_flutter_min_gpl/ffmpeg_kit.dart';
import 'package:path_provider/path_provider.dart';
import 'package:gallery_saver/gallery_saver.dart';

class VideoEditorState extends ChangeNotifier {
  File? _videoFile;
  VideoEditorController? _controller;

  File? get videoFile => _videoFile;
  VideoEditorController? get controller => _controller;

  Future<void> pickVideo() async {
    final picker = ImagePicker();
    final picked = await picker.pickVideo(source: ImageSource.gallery);
    if (picked != null) {
      _videoFile = File(picked.path);
      _controller?.dispose();
      _controller = VideoEditorController.file(_videoFile!)
        ..initialize().then((_) => notifyListeners());
      notifyListeners();
    }
  }

  double _exportProgress = 0.0;
  double get exportProgress => _exportProgress;

  bool _isExporting = false;
  bool get isExporting => _isExporting;

  Future<void> exportVideo({int? fps}) async {
    if (_videoFile == null) return;
    _isExporting = true;
    _exportProgress = 0;
    notifyListeners();

    final dir = await getTemporaryDirectory();
    final outPath = '${dir.path}/sanrio_motion_${DateTime.now().millisecondsSinceEpoch}.mp4';

    String fpsFilter = fps != null ? "-r $fps" : "";

    // Basic ffmpeg command to copy stream with different fps if provided
    final cmd = "-y -i '${_videoFile!.path}' $fpsFilter -c:v libx264 -preset veryfast -crf 18 -c:a copy '$outPath'";

    await FFmpegKit.executeAsync(cmd, (session) async {
      _isExporting = false;
      notifyListeners();
      final state = await session.getReturnCode();
      if (ReturnCode.isSuccess(state)) {
        await GallerySaver.saveVideo(outPath, albumName: "Sanrio Motion");
      }
    }, (log) {}, (statistics) {
      final total = statistics.getTime();
      final time = statistics.getVideoFrameNumber();
      if (total != 0) {
        _exportProgress = time / total;
        notifyListeners();
      }
    });
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }
}
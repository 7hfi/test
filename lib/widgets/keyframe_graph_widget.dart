import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

class KeyframeGraphWidget extends StatelessWidget {
  final List<FlSpot> points;
  const KeyframeGraphWidget({super.key, required this.points});

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1.8,
      child: Padding(
        padding: const EdgeInsets.all(8.0),
        child: LineChart(
          LineChartData(
            gridData: const FlGridData(show: false),
            titlesData: const FlTitlesData(show: false),
            borderData: FlBorderData(show: false),
            minX: 0,
            maxX: 1,
            minY: 0,
            maxY: 1,
            lineBarsData: [
              LineChartBarData(
                spots: points,
                isCurved: true,
                color: Theme.of(context).primaryColor,
                barWidth: 3,
                dotData: const FlDotData(show: true),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
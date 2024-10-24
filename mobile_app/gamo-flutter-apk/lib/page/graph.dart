import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import 'package:flutter_application_1/page/price_point.dart';

// This graph will diaply the last hour of data intervaled by 15 minutes
// Th x direction will have either normal time from start to stop or nothing
class LineChartWidget extends StatelessWidget {
  final List<PricePoint> points_tmp;
  final List<PricePoint> points_hum;
  final List<PricePoint> points_co2;

  const LineChartWidget(this.points_tmp, this.points_hum, this.points_co2,
      {Key? key})
      : super(key: key);

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 2,
      child: LineChart(
        LineChartData(
          lineBarsData: [
            LineChartBarData(
                spots: points_tmp
                    .map((point) => FlSpot(point.x, point.y))
                    .toList(),
                isCurved: false,
                dotData: FlDotData(
                  show: false,
                ),
                color: Colors.red),

            LineChartBarData(
                spots: points_hum
                    .map((point) => FlSpot(point.x, point.y))
                    .toList(),
                isCurved: false,
                dotData: FlDotData(
                  show: false,
                ),
                color: const Color.fromARGB(255, 27, 107, 173)),

            LineChartBarData(
                spots: points_co2
                    .map((point) => FlSpot(point.x, point.y))
                    .toList(),
                isCurved: false,
                dotData: FlDotData(
                  show: false,
                ),
                color: const Color.fromARGB(255, 14, 14, 14)),
          ],
          borderData: FlBorderData(),
          gridData: FlGridData(show: true),
          titlesData: FlTitlesData(
            bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
            leftTitles: AxisTitles(
                sideTitles: SideTitles(showTitles: true, reservedSize: 60)),
            topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
        ),
      ),
    );
  }

//
//! Change this into one hour divided by 5 minutes
//
  SideTitles get _bottomTitles => SideTitles(
        showTitles: false,
        getTitlesWidget: (value, meta) {
          String text = '';
          switch (value.toInt()) {
            case 1:
              text = '1H';
              break;
            case 2:
              text = '2H';
              break;
            case 3:
              text = '3H';
              break;
            case 4:
              text = '4H';
              break;
            case 5:
              text = '5H';
              break;
            case 6:
              text = '6H';
              break;
          }

          return Text(text);
        },
      );
}

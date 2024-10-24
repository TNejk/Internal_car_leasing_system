import 'dart:async';
import 'dart:convert';
import 'package:flutter_application_1/api/services.dart';
import 'package:flutter/material.dart';
import 'package:flutter_application_1/page/home.dart';
import 'package:flutter_application_1/scripts/storageWorker.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;

class SensorWidget extends StatefulWidget {
  //! NEED THE GATEWAY HERE
  final String sensorId;
  final FavoriteRooms favoriteRooms;
  final String nadr;
  final String gateway;
  final String token;
  // Add this line
  // Add this line
  const SensorWidget(
      {Key? key,
      required this.sensorId,
      required this.favoriteRooms,
      required this.nadr,
      required this.gateway,
      required this.token})
      : super(key: key);

  @override
  _SensorWidgetState createState() => _SensorWidgetState();
}

class _SensorWidgetState extends State<SensorWidget> {
  double temperature = 0.0;
  double humidity = 0;
  int ppm = 0;

  late Timer _timer;

  @override
  void initState() {
    super.initState();
    _fetchSensorData();
    _timer = Timer.periodic(Duration(seconds: 30), (Timer timer) {
      _fetchSensorData();
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  Future<void> _fetchSensorData() async {
    //print("DEBUG");
    //print(widget.sensorId);
    //print(widget.nadr);
    // Send the sensorID which is the name of a classroom
    try {
      var obj = Services();
      //print("OBJECT MESSAGE GATEWAY: " + widget.gateway);
      //print("OBJECT MESSAGE NAME: " + widget.sensorId);
      //print("DEBUG");
      //print(widget.gateway);
      //print(widget.nadr);
      http.Response response = await obj.getLastValues(
          "TOKENE TOKENE TOKENE TOKENE",
          widget.gateway,
          int.parse(widget.nadr));
      // data trucutre:
      if (response.statusCode == 200) {
        String vals = response.body;
        Map<String, dynamic> jsonData = jsonDecode(vals);
        //print(jsonData);
        // Extract data from the jsonData map
        // print("FETSH SENSOSR DATA CALLED  ;");
        // print(jsonData);
        var _temperature = jsonData['data'][2][1];
        var _humidity = jsonData['data'][0][1];
        var _ppm = jsonData['data'][1][1];

        // Do something with the extracted data
        setState(() {
          temperature = _temperature;
          humidity = _humidity;
          ppm = _ppm;
        });
      } else {
        // Handle error response
        print('Failed to fetch data: ${response.statusCode}');
      }
    } catch (e) {
      print(e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 5, bottom: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Padding(
                padding: const EdgeInsets.only(left: 10, right: 20),
                child: InkWell(
                  onLongPress: () {
                    // Get the index of the SensorWidget in the FavoriteRooms list
                    // print("DEBUG");
                    // print(widget.sensorId);
                    // print(widget.nadr);

                    int index =
                        widget.favoriteRooms.frooms.indexOf(this.widget);

                    widget.favoriteRooms.removeRoom(index);
                    StorageWorker(favoriteRooms: widget.favoriteRooms)
                        .deleteRoomFromJson(
                            widget.sensorId, widget.nadr.toString());
                    // Remove from json
                    //print("long ress ${widget.sensorId}, ${widget.nadr}");
                  },
                  onTap: () {
                    context.goNamed("room", queryParameters: {
                      "roomName": widget.sensorId,
                      "gateway": widget.gateway,
                      "nadr": widget.nadr,
                      "token": widget.token
                    });
                  },
                  child: Text(
                    "${widget.sensorId}",
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                )),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 10),
            child: Text('$temperature°C'),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 10),
            child: Text('$humidity%'),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 10),
            child: Text('$ppm PPM'),
          ),
        ],
      ),
    );
  }
}

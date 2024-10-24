import 'dart:convert';
    import 'dart:io' as io;
import 'package:flutter/widgets.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:flutter/material.dart';
import 'package:flutter_application_1/api/services.dart';
import 'package:flutter_application_1/page/graph.dart';
import 'package:flutter_application_1/page/price_point.dart';
import 'package:go_router/go_router.dart';
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:permission_handler/permission_handler.dart';
import 'package:intl/intl.dart';

class Room extends StatefulWidget {
  final String token;
  final String roomName;
  final String gateway;
  final String nadr;
  const Room(
      {super.key,
      required this.token,
      required this.roomName,
      required this.gateway,
      required this.nadr});

  @override
  State<Room> createState() => _RoomState();
}

class _RoomState extends State<Room> {
  // Add a variable to store the temperature (initially 23°C)

  // Graph variables
  List<PricePoint> points_tmp = [];
  List<PricePoint> points_hum = [];
  List<PricePoint> points_co2 = [];
  String selected = "";

  ////!
  double voltage = 0;
  double hum = 0;
  int ppm = 0;
  double temperature = 0.0;
  int indexValue = 2;

  String tempSymbol = "°C";
  String humidSymbol = "%";
  String ppmSymbol = "ppm";
  String indexSymbol = "°C";

  int chosen = 0;
  var _timer;

  @override
  void initState() {
    super.initState();
    // Simulate updating temperature after 15 seconds
    print("This is my widget gateway:");
    print(widget.gateway);
    _fetchSensorData();
    _fetchGraphData("TOKNE", widget.gateway, widget.nadr);

    _timer = Timer.periodic(Duration(seconds: 20), (Timer timer) {
      _fetchSensorData();
      _fetchGraphData("TOKEN TOKEN TOKEN TOKEN", widget.gateway, widget.nadr);
    });
  }

  Future<void> _fetchGraphData(token, gateway, nadr) async {
    try {
      var obj = Services();

      http.Response response = await obj.getGraphValues(token, gateway, nadr);

      if (response.statusCode == 200) {
        String vals = response.body;

        //print("JSON GRPAH DATA");
        //print(vals[0]);
        List<dynamic> dataList = jsonDecode(vals);
        print(dataList);
        // Temporary
        int _tmpVal = 0;
        List<double> _tmpTemp = [];
        List<double> _tmpHum = [];
        List<double> _tmpPpm = [];

        for (var element in dataList) {
          _tmpVal += 1;
          if (element[0] == "Temperature") {
            _tmpTemp.add(element[1]);
          } else if (element[0] == "Humidity") {
            _tmpHum.add(element[1]);
          } else {
            _tmpPpm.add(element[1].toDouble());
          }
          print(element[1]);
        }

        setState(() {
          points_tmp = [];
          points_hum = [];
          points_co2 = [];
          double g = 1.0;
          switch (selected) {
            case "temperature":
              for (var i in _tmpTemp.reversed) {
                points_tmp.add(PricePoint(x: g++, y: i));
              }
              break;
            case "humidity":
              for (var i in _tmpHum.reversed) {
                points_hum.add(PricePoint(x: g++, y: i));
              }
              break;
            case "co2":
              for (var i in _tmpPpm.reversed) {
                points_co2.add(PricePoint(x: g++, y: i));
              }
              break;
            default:
              for (var i in _tmpTemp.reversed) {
                points_tmp.add(PricePoint(x: g++, y: i));
              }
          }
        });

        _tmpVal = 0;
      } else {
        print('Failed to fetch data: ${response.statusCode}');
      }
    } catch (e) {
      print(e);
    }
  }

  Future<void> _fetchSensorData() async {
    try {
      var obj = Services();

      http.Response response = await obj.getLastValues(
          widget.token, widget.gateway, int.parse(widget.nadr));
      // data trucutre:
      if (response.statusCode == 200) {
        String vals = response.body;
        Map<String, dynamic> jsonData = jsonDecode(vals);
        setState(() {
          temperature = double.parse(jsonData["data"][2][1].toString());
          hum = double.parse(jsonData["data"][0][1].toString());
          ppm = int.parse(jsonData["data"][1][1].toString());
          voltage = jsonData["data"][3][1];
        });
        // 9): {data: [[Humidity, 55.0], [PPM, 483], [Temperature, 18.0]]}
      } else {
        print('Failed to fetch data: ${response.statusCode}');
      }
    } catch (e) {
      print(e);
    }
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  // Function to update temperature (replace with actual logic)

  @override
  Widget build(BuildContext context) {
    double width = MediaQuery.of(context).size.width;
    double height = MediaQuery.of(context).size.height;
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: () {
            Navigator.pop(context);
          },
          icon: Icon(Icons.arrow_back, size: 30),
        ),
        actions: [Padding(
          padding: const EdgeInsets.only(right:10.0),
          child: IconButton(onPressed: () {
            // * Show alarmbox if they weant to downlaod thingy
            // if yes then start a async function get data, create a pdf and save it to the documents folder
            //
            showDialog  ( context: context,
            builder: (BuildContext context) {
              return AlertDialog(
                title: Text("Chcete stiahnuť výpis senzora?"),
                content: Text("*ulozene do android/data/com.example.smarfe", style: TextStyle(fontSize: 9),),
                actions: [
                TextButton(onPressed: () async {

                  //! Get storage permissions
                  var status = await Permission.storage.status;
                  if (!status.isGranted) {
                  await Permission.storage.request();
                  }

                  String school = "";
                  if (widget.gateway == "sosit") {school = "SOS-IT";}
                  if (widget.gateway == "gymnazium") {school = "Gymnázium TJ";}
                  if (widget.gateway == "zakladna") {school = "Zakladna";}

                  var result = await Services().getPDFValues("TOKE  TONE TOKEN", widget.gateway, widget.nadr, school);
                  final data = jsonDecode(result.body) as Map<String, dynamic>;
                  
                  //! Get the current date
                  DateTime now = DateTime.now();
                  String formattedDate = DateFormat('kk:mm:ss EEE d MMM').format(now);


                  //! construct a PDF
                  final pdf = pw.Document();

                  pdf.addPage(pw.Page(
                        pageFormat: PdfPageFormat.a4,
                        build: (pw.Context context) {
                          return pw.Column(children: [
                            pw.Text("${data["sens"]["name"]}", style: pw.TextStyle(fontSize: 30, fontWeight: pw.FontWeight.bold)),
                            pw.SizedBox(height: 3),
                            pw.Divider(),
                            pw.SizedBox(height: 40),
                        
                            pw.Text("Info", style: pw.TextStyle(fontSize: 15, fontWeight: pw.FontWeight.bold)),
                            pw.SizedBox(height: 5),
                            pw.Row(children: [pw.Text("Model: NLB-CO2+RH+T-5-IQRF")]),
                            pw.Row(children: [pw.Text("NADR: ${data["sens"]["nadr"]}")]),
                            pw.Row(children: [pw.Text("Gateway: ${data["sens"]["gateway"]}")]),
                            pw.Row(children: [pw.Text("School: ${data["sens"]["sensor_school"]}")]),
                            pw.SizedBox(height: 20),
                            pw.Text("Status", style: pw.TextStyle(fontSize: 15, fontWeight: pw.FontWeight.bold)),
                            pw.SizedBox(height: 5),
                            pw.Row(children: [pw.Text("health: ${data["sens"]["sens_status"]}")]),
                            pw.Row(children: [pw.Text("battery: ${data["sens"]["battery"]}")]),
                            pw.SizedBox(height: 20),
                            pw.Text("Data trend", style: pw.TextStyle(fontSize: 15, fontWeight: pw.FontWeight.bold)),
                            pw.SizedBox(height: 5),
                            pw.Row(children: [pw.Text("TMP: ${data["trends"]["tmp_trend"]}")]),
                            pw.Row(children: [pw.Text("HUM: ${data["trends"]["hum_trend"]}")]),
                            pw.Row(children: [pw.Text("CO2: ${data["trends"]["co2_trend"]}")]),
                            pw.SizedBox(height: 5),
                            pw.Text("Last data", style: pw.TextStyle(fontSize: 15, fontWeight: pw.FontWeight.bold)),
                            pw.Row(children: [pw.Text("TMP: ${data["sens"]["tmp"]}")]),
                            pw.Row(children: [pw.Text("HUM: ${data["sens"]["hum"]}")]),
                            pw.Row(children: [pw.Text("CO2: ${data["sens"]["co2"]}")]),
                            pw.SizedBox(height: 40),
                            pw.Expanded(
                              child: pw.Footer(leading: pw.Text("${formattedDate}"),title: pw.Text("S.M.A.R.F.E report"), trailing: pw.Text("SOS IT, BB"))
                          
                              )
                          

                          ]);
                        })); 

                // ! Save the PDF
                final output = await getExternalStorageDirectory();
                final path = "${output!.path}/smarfe-report:${data["sens"]["nadr"]}-${data["sens"]["gateway"]}.pdf";
                // check comment!
                await io.File(path).writeAsBytes(await pdf.save()); // ! added await before the pdf.save() to convert hte Future list into a List<int>
                Navigator.pop(context);

                }, child: Text("Ano")), 
                TextButton(onPressed: () {Navigator.pop(context);}, child: Text("Nie"))
                ],
              );
            },);
          }, icon: Icon(Icons.download, size: 30,)),
        )],
        backgroundColor: Colors.red,
      ),
      body: Column(
        children: [
          SizedBox(
            height: height * 0.01,
          ),
          Container(
            child: Padding(
              padding: const EdgeInsets.only(top: 10.0, left: 10, right: 10),
              child: Text(
                widget.roomName,
                style: TextStyle(fontSize: 41, fontWeight: FontWeight.bold),
              ),
            ),
          ),
          Text("Graf z posledných troch hodín"),
          SizedBox(
            height: height * 0.08,
          ),
          Padding(
            padding: EdgeInsets.only(
              right: width * 0.10,
              left: width * 0.05,
            ),
            child: LineChartWidget(points_tmp, points_hum, points_co2),
          ),
          Padding(
            padding: EdgeInsets.only(
                left: width * 0.10, right: width * 0.10, top: height * 0.05),
            child: Container(
                decoration: BoxDecoration(
                  color: const Color.fromARGB(255, 255, 255, 255),
                ),
                child: Column(children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(left: 0.0),
                        child: Text(
                          "Teplota:",
                          style: TextStyle(
                              fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.only(right: 0.0),
                        child: Text("$temperature°C",
                            style: TextStyle(
                                fontSize: 16, fontWeight: FontWeight.bold)),
                      )
                    ],
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(left: 0.0),
                        child: Text("Vlhkosť:",
                            style: TextStyle(
                                fontSize: 16, fontWeight: FontWeight.bold)),
                      ),
                      Padding(
                        padding: const EdgeInsets.only(right: 0.0),
                        child: Text("$hum%",
                            style: TextStyle(
                                fontSize: 16, fontWeight: FontWeight.bold)),
                      )
                    ],
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(left: 0.0),
                        child: Text("Co2:",
                            style: TextStyle(
                                fontSize: 16, fontWeight: FontWeight.bold)),
                      ),
                      Padding(
                        padding: const EdgeInsets.only(right: 0.0),
                        child: Text("$ppm PPM",
                            style: TextStyle(
                                fontSize: 16, fontWeight: FontWeight.bold)),
                      )
                    ],
                  ),
                  Divider(),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(left: 0.0),
                        child: Text("Voltage:",
                            style: TextStyle(
                                fontSize: 16, fontWeight: FontWeight.bold)),
                      ),
                      Padding(
                        padding: const EdgeInsets.only(right: 0.0),
                        child: Text("$voltage V",
                            style: TextStyle(
                                fontSize: 16, fontWeight: FontWeight.bold)),
                      )
                    ],
                  ),
                ])),
          ),
          SizedBox(
            height: height * 0.07,
          ),
          Padding(
            padding: EdgeInsets.only(left: width * 0.05, right: width * 0.05),
            child: Container(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  Container(
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.black, width: 2),
                      borderRadius: BorderRadius.all(Radius.circular(10)),
                    ),
                    child: IconButton(
                      iconSize: width * 0.14,
                      onPressed: () {
                        setState(() {
                          indexValue = 2;
                          indexSymbol = tempSymbol;
                          selected = "temperature";
                        });
                        _fetchGraphData(
                            "TOKEN TOKEN TOKEN", widget.gateway, widget.nadr);
                      },
                      icon: Icon(Icons.thermostat),
                    ),
                  ),
                  Container(
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.black, width: 2),
                      borderRadius: BorderRadius.all(Radius.circular(10)),
                    ),
                    child: IconButton(
                      iconSize: width * 0.14,
                      onPressed: () {
                        setState(() {
                          indexValue = 0;
                          indexSymbol = humidSymbol;
                          selected = "humidity";
                        });
                        _fetchGraphData(
                            "TOKEN TOKEN TOKEN", widget.gateway, widget.nadr);
                      },
                      icon: Icon(Icons.cloud),
                    ),
                  ),
                  Container(
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.black, width: 2),
                      borderRadius: BorderRadius.all(Radius.circular(10)),
                    ),
                    child: IconButton(
                      iconSize: width * 0.14,
                      onPressed: () {
                        setState(() {
                          indexValue = 1;
                          indexSymbol = ppmSymbol;
                          selected = "co2";
                        });
                        _fetchGraphData(
                            "TOKEN TOKEN TOKEN", widget.gateway, widget.nadr);
                      },
                      icon: Icon(Icons.co2),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
      bottomSheet: Container(
        height: 30,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Padding(
              padding: EdgeInsets.only(left: 10),
              child: Text("SOS IT, BB "),
            ),
            Padding(
              padding: EdgeInsets.only(right: 10),
              child: Text("All rights reserved"),
            ),
          ],
        ),
      ),
    );
  }
}

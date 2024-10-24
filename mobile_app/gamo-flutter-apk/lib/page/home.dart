import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter_application_1/widgets/favoriteWidget.dart';

import 'package:provider/provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_application_1/api/services.dart';
import 'package:flutter_application_1/scripts/storageWorker.dart';
import 'package:go_router/go_router.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final searchBoxController = TextEditingController();

  @override
  Widget build(BuildContext context) {
    double width = MediaQuery.of(context).size.width;
    double height = MediaQuery.of(context).size.height;

    return 
    PopScope(child: 
    Scaffold(
        resizeToAvoidBottomInset: false,
        bottomSheet: Container(
            height: 30,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Padding(
                  padding: EdgeInsets.only(left: 10),
                  child: Text("SOS IT, BB"),
                ),
                Padding(
                  padding: EdgeInsets.only(right: 10),
                  child: Text(" All rights reserved"),
                )
              ],
            )),
        drawerEdgeDragWidth: width * 0.70,
        drawer: CustomDrawer(
          token: "TOKEN TOKEN TOKEN TOKEN TOKEN",
          key: widget.key,
        ),
        appBar: AppBar(
          centerTitle: true,
          backgroundColor: Colors.red[400],
          primary: true,

          title: Text("Domov"),
        ),
        body: Column(children: [
          Content(
            Pcontext: context,
          )
        ]
        )
    )
    , canPop: false);
  }
}

//! Change Notifier CLASS
class FavoriteRooms extends ChangeNotifier {
  List<SensorWidget> frooms = [];

  void addRoom(SensorWidget room) {
    frooms.add(room);
    notifyListeners(); // Notify listeners about the change
  }

  void removeRoom(int index) {
    if (index >= 0 && index < frooms.length) {
      frooms.removeAt(index);
      notifyListeners(); // Notify listeners about the change
    }
  }
}

//! Main content Widget
class Content extends StatefulWidget {
  final BuildContext Pcontext;
  Content({super.key, required this.Pcontext});

  @override
  State<Content> createState() => _ContentState();
}

class _ContentState extends State<Content> {
  //List<Container> rooms = [];
  int sens = 0;
  double temp = 0.0;
  double vlhkost = 0.0;
  double ppm = 0;
  int score = 0;

  String enumeration_choice = "sosit";
  var not_obj = FavoriteRooms();

  Future<void> _loadRooms() async {
    var obj = StorageWorker(favoriteRooms: not_obj);
    List<SensorWidget> loadedRooms =
        await obj.returnListTiles("TOKEN TOKEN TOKNE TOKEN TOKEN");
    for (var i in loadedRooms) {
      not_obj.addRoom(i);
    }
  }

  @override
  // Initilaite the enumaretion timer and load rooms for the favorite rooms section
  void initState() {
    super.initState();
    _loadRooms();
    Timer.periodic(Duration(seconds: 30), (timer) {
      // get data
      setEnumerateValues();
    });

    //StorageWorker().addRoomToJson("308", "sdsd", "1");
    //StorageWorker(favoriteRooms: not_obj).deleteFileContent();
  }

  //! recvGraphData(token, time).then((http.Response response) {
  Future<Map<String, dynamic>> setEnumerateValues() async {
    //try {
    final response = await Services()
        .getEnumeration("TOKEN TOKEN TOKEN", enumeration_choice);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      print("Setting Enumearet values");
      print(data);
      setState(() {
        // {rooms: {humidity: 57.35, ppm: 940.6333333333333, score: -110, sensors: 1, temperature: 19.814583333333335}}

        // I/flutter ( 4586): {rooms: {humidity: 57.284615384615385, ppm: 939.8153846153846, score: 10, sensors: 1, temperature: 19.828846153846154}}
        // I/flutter ( 4586): Error fetching enumeration data: type 'int' is not a subtype of type 'String'
        // E/flutter ( 4586): [ERROR:flutter/runtime/dart_vm_initializer.cc(41)] Unhandled Exception: Exception: Failed to fetch enumeration data
        // E/flutter ( 4586): #0      _ContentState.setEnumerateValues (package:flutter_application_1/page/home.dart:188:7)
        // E/flutter ( 4586): <asynchronous suspension>

        // TODO: FIX THIS SHIT
        //var _tmp = data["rooms"]["sensors"];
        //print("Data type of sens: ${_tmp.runtimeType}");
        //
        //? Clear the values just to be safe
        sens = 0;
        temp = 0.0;
        vlhkost = 0.0;
        ppm = 0.0;
        score = 0;

        sens = data["rooms"]["sensors"];
        temp = double.parse(data["rooms"]["temperature"]);
        vlhkost = double.parse(data["rooms"]["humidity"]);
        ppm = double.parse(data["rooms"]["ppm"]);
        score = int.parse(data["rooms"]["score"]);
      });
      return data;
    } else {
      print(
          'Error fetching enumeration data: Status code ${response.statusCode}');
      throw Exception('Failed to fetch enumeration data');
    }
    // } catch (error) {
    //   print('Error fetching enumeration data: $error');
    //   throw Exception('Failed to fetch enumeration data');
    // }
  }

  Future<List<dynamic>> getSenzorList() async {
    print("VALUE CHANGED");
    // Replace with logic to get new temperat
    var response = await Services().getFavoriteRooms("TOKEN TOKEN TOKEN TOKEN");
    var jsonData = jsonDecode(response.body);
    return jsonData["rooms"];
  }

  // void updateRoomsDEBUG() async {
  //   List<Container> tmp = await StorageWorker().returnListTiles();
  //   setState(() {
  //     // TODO: somehow update the fkin list like holy shit
  //     rooms = tmp;
  //   });

  // print("Updated.");
  // }

  @override
  Widget build(BuildContext context) {
    double width = MediaQuery.of(context).size.width;
    double height = MediaQuery.of(context).size.height;

    return ChangeNotifierProvider<FavoriteRooms>(
        create: (context) => not_obj,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.start,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            //!
            //! Searchbox
            //!

            SizedBox(
              height: height * 0.05,
            ),
            //!
            //! Rýchla voľba
            //!
            Padding(
              padding: EdgeInsets.only(left: width - width * 0.85),
              child: Row(
                children: [
                  Text(
                    "Prehľad",
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  IconButton(
                    icon: Padding(
                      padding: EdgeInsets.only(left: width - width * 0.53),
                      child: Icon(Icons.school),
                    ),
                    onPressed: () {
                      // showdialog
                      showDialog(
                          context: context,
                          builder: (BuildContext context) {
                            return AlertDialog(
                              
                              backgroundColor: Colors.grey[200],
                              content: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  TextButton(
                                    onPressed: () {
                                      setState(() {
                                        enumeration_choice = "sosit";
                                      });

                                      context.pop(context);
                                      setEnumerateValues();
                                    },
                                    child: Text(
                                      "SOS-IT",
                                      style: TextStyle(
                                          color: Colors.black, fontSize: 15),
                                    ),
                                  ),
                                  TextButton(
                                    onPressed: () {
                                      setState(() {
                                        enumeration_choice = "gymnazium";
                                      });

                                      context.pop(context);
                                      setEnumerateValues();
                                    },
                                    child: Text("Gymnázium",
                                        style: TextStyle(
                                            color: Colors.black, fontSize: 15)),
                                  ),
                                  TextButton(
                                    onPressed: () {
                                      setState(() {
                                        enumeration_choice = "zakladna";
                                      });

                                      context.pop(context);
                                      setEnumerateValues();
                                    },
                                    child: Text("ZS",
                                        style: TextStyle(
                                            color: Colors.black, fontSize: 15)),
                                  ),
                                ],
                              ),
                            );
                          });
                    },
                  )
                ],
              ),
            ),

            Container(
              width: width - width * 0.25,
              decoration: BoxDecoration(
                  border: Border.all(color: Colors.black, width: 2)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Padding(
                    padding:
                        EdgeInsets.only(left: 20, right: 5, top: 5, bottom: 5),
                    child: Text("Počet senzorov: ${sens}"),
                  ),
                  Padding(
                    padding:
                        EdgeInsets.only(left: 20, right: 5, top: 5, bottom: 5),
                    child: Text("Priemerná teplota: ${temp}°C"),
                  ),
                  Padding(
                    padding:
                        EdgeInsets.only(left: 20, right: 5, top: 5, bottom: 5),
                    child: Text("Priemerná vlhkosť: ${vlhkost}%"),
                  ),
                  Padding(
                    padding:
                        EdgeInsets.only(left: 20, right: 5, top: 5, bottom: 5),
                    child: Text("Priemerné PPM: ${ppm}"),
                  ),
                  Padding(
                    padding:
                        EdgeInsets.only(left: 20, right: 5, top: 10, bottom: 5),
                    child: Text(
                      "Kvalita T.V.P. v škole: ${score}/10",
                      style: TextStyle(fontWeight: FontWeight.w500),
                    ),
                  ),
                ],
              ),
            ),
            //!
            //!  Alert Dialog pre Obľúbené miestnosti
            //!
            SizedBox(
              height: height * 0.10,
            ),
            Consumer<FavoriteRooms>(
              builder: (context, favoriteRooms, child) => Padding(
                padding: EdgeInsets.only(left: width - width * 0.85),
                child: Row(
                  children: [
                    Text("Obľúbené senzory",
                        style: TextStyle(fontWeight: FontWeight.bold)),
                    IconButton(
                      onPressed: () async {
                        showDialog(
                            context: context,
                            builder: (BuildContext context) {
                              return AlertDialog(
                                content: FutureBuilder<List<dynamic>>(
                                    future:
                                        getSenzorList(), //! This calls the service class and HTTP requests the server for a list of available senzors, from it you can recieve the gateways
                                    builder: (BuildContext context,
                                        AsyncSnapshot<List<dynamic>> snapshot) {
                                      if (snapshot.hasData) {
                                        //print(snapshot.data);
                                        List<Widget> _room = [];
                                        for (var element in snapshot.data!) {
                                          _room.add(TextButton(
                                              onPressed: () async {
                                                // Save dashboard list to JSON
                                                // somehow get the index of the list
                                                String generateRandomString(
                                                    int len) {
                                                  var r = Random();
                                                  return String.fromCharCodes(
                                                      List.generate(
                                                          len,
                                                          (index) =>
                                                              r.nextInt(33) +
                                                              89));
                                                }

                                                var ind =
                                                    generateRandomString(10);
                                                generateRandomString(10);
                                                StorageWorker(
                                                        favoriteRooms:
                                                            favoriteRooms)
                                                    .addRoomToJson(
                                                        element["name"],
                                                        "token",
                                                        element["nadr"],
                                                        element["gateway"]);
                                                // add the key to the favorite rooms list maybe?
                                                favoriteRooms.addRoom(
                                                  SensorWidget(
                                                    // Assign a key here
                                                    key: Key("sens$ind"),
                                                    sensorId: element["name"],
                                                    favoriteRooms: not_obj,
                                                    nadr: element["nadr"],
                                                    gateway: element["gateway"],
                                                    token: "TOKEN TOKEN ROKEN",
                                                  ),
                                                );
                                                // print(element["gateway"]);
                                                // print(element["nadr"]);
                                                // print(element["name"]);
                                                Navigator.pop(context);
                                              },
                                              child: Text(
                                                element["name"],
                                                style: TextStyle(
                                                    fontSize: 16,
                                                    color: Colors.black),
                                              )));
                                        }
                                        return Container(
                                          height: 200,
                                          width: width - width * 0.20,
                                          child: Center(
                                            child: ListView(
                                              //! This is a listview for the AlertDialog!!!
                                              children: _room,
                                            ),
                                          ),
                                        );
                                      } else if (snapshot.hasError) {
                                        return Text("${snapshot.error}");
                                      } else {
                                        return CircularProgressIndicator();
                                      }
                                    }),
                              );
                            });

                        //! DEBUG DEBUG DEBUG DELTE LATER IF NOT WORK

                        //updateRoomsDEBUG();
                      },
                      icon: Padding(
                        padding: EdgeInsets.only(left: width - width * 0.70),
                        child: Icon(Icons.add),
                      ),
                    )
                  ],
                ),
              ),
            ),

            //! Favorite Rooms
            // is a consumer of the Change notifier
            Consumer<FavoriteRooms>(
              builder: (context, favoriteRooms, child) => Container(
                width: width - width * 0.25,
                height: height * 0.20,
                decoration: BoxDecoration(
                    border: Border.all(color: Colors.black, width: 2)),
                child: ListView.builder(
                  itemCount: not_obj.frooms.length,
                  itemBuilder: (BuildContext context, int index) {
                    //print(not_obj.frooms);
                    // This adds a SensorWidget for every element, (the elemets itself are the SensorWidgets)
                    print(not_obj.frooms[index]);

                    return not_obj.frooms[index];
                  },
                ),
              ),
            ),

            //List<Widget>.from(gameState.gcurrentPlayers[0].ownList),
            //!
            //! Všetky senzory
            //!
            Padding(
              padding:
                  EdgeInsets.only(bottom: height * 0.10, top: height * 0.04),
              child: Container(
                width: width - width * 0.25,
                decoration: BoxDecoration(
                    border: Border.all(color: Colors.black, width: 2)),
                child: Padding(
                  padding:
                      const EdgeInsets.only(top: 10.0, bottom: 10, left: 20),
                  child: Column(children: [
                    Row(
                      children: [
                        Icon(
                          size: 35,
                          Icons.leaderboard,
                          //Icons.sensors,
                          color: Colors.red,
                        )
                      ],
                    ),
                    Row(
                      children: [
                        Text(
                          "Leaderboard",
                          style: TextStyle(fontSize: 18),
                        ),
                        Padding(
                          padding: EdgeInsets.only(left: width - width * 0.80),
                          child: IconButton(
                              onPressed: () {
                                context.goNamed("senzors", queryParameters: {"token": "TOKEN TOKEN TOKEN TOKEN"});
                              },
                              icon: Icon(
                                size: 35,
                                Icons.arrow_forward,
                                color: Colors.red,
                              )),
                        )
                      ],
                    )
                  ]),
                ),
              ),
            )
          ],
        ));
  }
}

class CustomDrawer extends StatefulWidget {
  final String token;
  const CustomDrawer({required this.token, super.key});

  @override
  State<CustomDrawer> createState() => _CustomDrawerState();
}

class _CustomDrawerState extends State<CustomDrawer> {
  dynamic jsonData;
  // Function for nested parsing of JSON data

  //
  //

  // Define your future function here (replace with your actual implementation)
  Future<dynamic> loadJsonAsset() async {
    final String jsonString =
        await rootBundle.loadString('assets/roomList.json');
    var data = jsonDecode(jsonString);
    return data;
  }

  @override
  Widget build(BuildContext context) {
    return Drawer(
      backgroundColor: Color.fromARGB(166, 248, 237, 231),
      child: Container(
        color: Color.fromARGB(166, 248, 237, 231),
        child: ListView(
          children: [
            Image(image: AssetImage("assets/ooo.png")),
            FutureBuilder(
              future: loadJsonAsset(),
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return Center(
                    child: CircularProgressIndicator(),
                  );
                } else if (snapshot.hasError) {
                  return Center(
                    child: Text('Error loading data'),
                  );
                } else if (snapshot.connectionState == ConnectionState.done) {
                  jsonData = snapshot.data;
                  List<CustomExpansionTile> sections = [];
                  try {
                    for (var key in jsonData.keys) {
                      // Loops Roots
                      List<CustomExpansionTile> floors = [];
                      List<DrawerTileWidget> senzors = [];

                      if (jsonData[key] is Map<String, dynamic>) {
                        print("$key is a Map"); //key == Root expansionTile Name
                        Map<String, dynamic> innerMap = jsonData[key];

                        for (var innerKey in innerMap.keys) {
                          if (innerMap[innerKey] is List<dynamic>) {
                            print("$innerKey is a List");

                            for (var item in innerMap[innerKey]) {
                              senzors.add(DrawerTileWidget(
                                name: item["roomName"],
                                gateway: item["gateway"],
                                nadr: item["nadr"],
                                token: widget.token,
                              ));
                            }

                            floors.add(CustomExpansionTile(
                                isSub: true, data: innerKey, rooms: senzors));
                            senzors = [];
                          }
                        }

                        sections.add(CustomExpansionTile(
                            isSub: false, data: key, rooms: floors));
                        floors = [];
                      }
                    }
                  } on Exception catch (e) {
                    print("CATCH ERROR");
                    print(e);
                  }

                  return Column(
                    children: sections,
                  );
                } else {
                  return Text(
                      "An error has occured, rerun the App or contact the admins");
                }
              },
            ),
   
          ],
        ),
      ),
    );
  }
}

//! EXPANSION TILE
//
//
class CustomExpansionTile extends StatefulWidget {
  final bool isSub;
  final String data;
  final List<Widget> rooms;

  const CustomExpansionTile({
    super.key,
    required this.isSub,
    required this.data,
    required this.rooms,
  });

  @override
  State<CustomExpansionTile> createState() => _CustomExpansionTileState();
}

class _CustomExpansionTileState extends State<CustomExpansionTile> {
  @override
  Widget build(BuildContext context) {
    return Container(
        child: Padding(
      padding:
          widget.isSub ? const EdgeInsets.only(left: 16.0) : EdgeInsets.zero,
      child: ExpansionTile(
          maintainState: true,
          textColor: Color.fromARGB(255, 0, 0, 0),
          collapsedTextColor: const Color.fromARGB(255, 0, 0, 0),
          iconColor: Color.fromARGB(255, 0, 0, 0),
          collapsedIconColor: const Color.fromARGB(255, 0, 0, 0),
          leading: Text(widget.data,
              style: const TextStyle(
                  fontSize: 18, color: Color.fromARGB(255, 0, 0, 0))),
          title: SizedBox(),
          children: widget.rooms // widget.rooms is a widget list List<Widget>
          ),
    ));
  }
}

class DrawerTileWidget extends StatefulWidget {
  final String name;
  final String gateway;
  final String nadr;
  final String token;
  const DrawerTileWidget(
      {required this.name,
      required this.nadr,
      required this.gateway,
      required this.token,
      super.key});

  @override
  State<DrawerTileWidget> createState() => _DrawerTileWidgetState();
}

class _DrawerTileWidgetState extends State<DrawerTileWidget> {
  @override
  void initState() {
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return ListTile(
      title: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          Center(
            child: TextButton(
              onPressed: () {
                context.goNamed("room", queryParameters: {
                  "roomName": widget.name,
                  "gateway": widget.gateway,
                  "nadr": widget.nadr,
                  "token": widget.token
                });
              },
              child: Text(widget.name,
                  style: TextStyle(color: Color.fromARGB(255, 0, 0, 0))),
            ),
          ),
        ],
      ),
    );
  }
}

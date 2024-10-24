import 'dart:convert';
import 'dart:ffi';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_application_1/api/services.dart';
import 'package:http/http.dart' as http;

class SenzorList extends StatefulWidget {
  final String token;
  const SenzorList({
    super.key,
    required this.token
    });

  @override
  State<SenzorList> createState() => _SenzorListState();
}

class _SenzorListState extends State<SenzorList> {
    List<dynamic> schools = [];

    Future<void>  get_scoreboard(token) async{
      var obwj = Services();
      http.Response response = await obwj.getScore(token);

      if (response.statusCode == 200) {
        String vals = response.body;
        Map<String, dynamic> dataList = jsonDecode(vals);
        print("sdsdsdsds");
        print(dataList);
        setState(() {
          schools.addAll(dataList["ordered"]);
        });
      } else {
        print("No data found");
        return null;
      };
    }

    @override
    void initState() {
      super.initState();
      // Get scoreboard data
      print("getting data");
      get_scoreboard(widget.token);
    }


  @override
  Widget build(BuildContext context) {
    double width = MediaQuery.of(context).size.width;
    double height = MediaQuery.of(context).size.height;
        // "ordered": [
        //     {
        //         "name": "SOS-IT",
        //         "score": 2991,
        //         "place": 1
        //     },
        //                 {
        //         "name": "Gymnázium",
        //         "score": 2991,
        //         "place": 2
        //     },
        //                 {
        //         "name": "Zakladná",
        //         "score": 2991,
        //         "place": 3
        //     },
        //     ]


    return Scaffold(
        appBar: AppBar(
            leading: IconButton(
                onPressed: () {
                  // ROUTE CONTEXT TO DASHBOARD
                  context.goNamed("home");
                },
                icon: Icon(Icons.arrow_back)),
            title: Text("Leaderboard"),
            centerTitle: true,
            backgroundColor: Colors.red[400]),
        body: 
            ListView.builder(
              itemCount: schools.length,
              itemBuilder: (BuildContext context, int index) {
                return ListElement(
                  name: schools[index]["name"], 
                  score: schools[index]["score"], 
                  place: schools[index]["place"]
                  );
              },
        ),
    );
  }
}


// This is fed into the listview builder 
class ListElement extends StatelessWidget {
 final String name;
 final int score;
 final int place;

 const ListElement({
    super.key,
    required this.name,
    required this.score,
    required this.place
    });

 @override
 Widget build(BuildContext context) {
  var tilecol;
  switch (place) {
    case 1:
      tilecol = Color.fromARGB(235, 255, 215, 0);; //r: 255, g: 215, b: 0
      break;

    case 2:
      tilecol = Color.fromARGB(235, 192, 192, 192);; // r: 192, g: 192, b: 192
      break;

    case 3:
      tilecol = Color.fromARGB(235, 205, 127, 50); // rgb(205, 127, 50)
      break;
    default:
      tilecol = Colors.white;
  }
  return ListTile(
    
    tileColor: tilecol,
    title: Text(name),
    leading: Text(place.toString()),
    trailing: Text(score.toString()),
    );
 }
}
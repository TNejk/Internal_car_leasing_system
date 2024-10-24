import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'package:flutter_application_1/page/home.dart';
import 'package:flutter_application_1/widgets/favoriteWidget.dart';
import 'package:go_router/go_router.dart';
import 'package:path_provider/path_provider.dart';
import 'package:flutter/material.dart';

class StorageWorker {
  final FavoriteRooms favoriteRooms;
// 	"rooms": [
// 	{
// 	"name": "uuu",
// 	"token": "sdsd",
// 	"nadr": "wšľš"
// 	}
// ]

  const StorageWorker({
    required this.favoriteRooms,
  });

  Future<String> getLocalPath() async {
    final directory = await getApplicationDocumentsDirectory();
    return directory.path;
  }

  Future<bool> addRoomToJson(
      String newName, String newToken, String newNadr, String gateway) async {
    // Step 1: Load existing JSON data
    var path = await getLocalPath();
    File file = File(path + 'favorite_rooms.json');
    String jsonContent = await file.readAsString();

    // Step 2: Parse JSON data into Dart object
    Map<String, dynamic> data = json.decode(jsonContent);

    // Step 3: Add a new element to the Dart object
    Map<String, dynamic> newRoom = {
      'name': newName,
      'token': newToken,
      'nadr': newNadr,
      'gateway': gateway
    };
    data['rooms'].add(newRoom);

    // Step 4: Convert the updated Dart object back to JSON
    String updatedJson = json.encode(data);

    // Step 5: Save the updated JSON data
    await file.writeAsString(updatedJson);
    return true;
  }

  // Read rooms
  Future<Map<String, dynamic>> readRooms() async {
    var path = await getLocalPath();
    File file = File(path + 'favorite_rooms.json');
    String jsonContent = await file.readAsString();

    // Step 2: Parse JSON data into Dart object
    Map<String, dynamic> data = json.decode(jsonContent);
    return data;
  }

  // Delete rooms
  Future<bool> deleteRoomFromJson(String name, String nadr) async {
    // Get path
    var path = await getLocalPath();
    File file = File(path + 'favorite_rooms.json');
    String jsonContent = await file.readAsString();

    // Parse JSON data into Dart object
    Map<String, dynamic> data = json.decode(jsonContent);

    // Search for the element that matches the provided arguments
    List<dynamic> rooms = data['rooms'];
    int indexToRemove = -1;
    for (int i = 0; i < rooms.length; i++) {
      if (rooms[i]['name'].toString() == name &&
          rooms[i]['nadr'].toString() == nadr) {
        indexToRemove = i;
        break;
      } else {
        // contemplate life
      }
    }
    // If found, remove the element from the Dart object
    if (indexToRemove != -1) {
      data['rooms'].removeAt(indexToRemove);
    } else {
      print('Element not found.');
      return false;
    }

    String updatedJson = json.encode(data);

    // Save the JSON 
    await file.writeAsString(updatedJson);
    return true;
  }

  Future<List<SensorWidget>> returnListTiles(String token) async {
    // Step 1: Check if file exists, if not create it
    var path = await getLocalPath();
    File file = File(path + 'favorite_rooms.json');
    if (!file.existsSync()) {
      file.createSync();
    }

    // Step 2: Check if file is empty, if it is, input a skeleton of JSON
    if (file.lengthSync() == 0) {
      file.writeAsStringSync('{\n  "rooms": [\n  ]\n}\n');
      print("Initialized favorite rooms file with json");
    }

    // try {

    String jsonString = await file.readAsString();

    Map<String, dynamic> jsonData = jsonDecode(jsonString);

    List<dynamic> roomsData = jsonData['rooms'];
    //print(roomsData);

    //! Here you need to parse the gateway ID
    List<SensorWidget> parsedRooms = [];

    String generateRandomString(int len) {
      var r = Random();
      return String.fromCharCodes(
          List.generate(len, (index) => r.nextInt(33) + 89));
    }

    var ind = generateRandomString(10);
    generateRandomString(10);
    roomsData.forEach((roomData) {
      //print(roomData["name"]);
      //print(roomData["nadr"]);
      parsedRooms.add(SensorWidget(
        key: Key("sens$ind"),
        sensorId: roomData["name"],
        nadr: "${roomData["nadr"]}",
        gateway: roomData["gateway"],
        favoriteRooms: favoriteRooms,
        token: token,
      ));
    });

    return parsedRooms;
    // } catch (e) {
    //   print(e);
    //   print("ERTZUIORTZUIOERTZUIOERTZUIORTZUIOERTZUIORTZUIRTZUI");

    //   return [];
    // }
  }

  //! DEBUG DELETE LATER
  Future<void> deleteFileContent() async {
    // Step 1: Open the file in write mode
    var path = await getLocalPath();
    File file = File(path + 'favorite_rooms.json');
    RandomAccessFile raf = await file.open(mode: FileMode.write);

    try {
      // Step 2: Truncate the file to remove all its content
      await raf.truncate(0);
      print('File content deleted successfully.');
    } catch (e) {
      print('Error deleting file content: $e');
    } finally {
      // Step 3: Close the file
      await raf.close();
    }
  }
}

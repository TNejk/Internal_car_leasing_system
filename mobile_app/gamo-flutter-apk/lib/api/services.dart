import 'package:http/http.dart' as http;
import 'dart:convert';

class Services {
  Future<http.Response> loginResult(String name, String pass) {
    return http.post(
      Uri.parse('https://api.smarfe.sosit-wh.net/gamo-api/login'),
      headers: <String, String>{
        'Content-Type': 'application/json; charset=UTF-8',
      },
      body: jsonEncode(<String, String>{'name': name, 'password': pass}),
    );
  }

  // Future<http.Response> getLastValues() {
  //   return http.get(
  //     Uri.parse('http://192.168.0.91:5220/gamo-api/last_value'),
  //   );
  // }

  
  // NADR + Gateway + The token to send
  Future<http.Response> getLastValues(String token, String gateway, int nadr) {
    //print(gateway);
    //print(nadr);
    return http.post(
      Uri.parse('https://api.smarfe.sosit-wh.net/gamo-api/last_value'),
      headers: <String, String>{
        'Content-Type': 'application/json; charset=UTF-8',
      },
      body: jsonEncode(<String, String>{
        'token': token,
        "gateway": gateway,
        "nadr": nadr.toString()
      }),
    );
  }

  Future<http.Response> getFavoriteRooms(String token) {
    return http.post(
      Uri.parse('https://api.smarfe.sosit-wh.net/gamo-api/favorite_rooms'),
      headers: <String, String>{
        'Content-Type': 'application/json; charset=UTF-8',
      },
      body: jsonEncode(<String, String>{'token': token}),
    );
  }



  Future<http.Response> getScore(String token) {
    return http.post(
      Uri.parse('https://api.smarfe.sosit-wh.net/gamo-api/scoreboard'),
      headers: <String, String>{
        'Content-Type': 'application/json; charset=UTF-8',
      },
      body: jsonEncode(<String, String>{'token': token}),
    );
  }




  Future<http.Response> getEnumeration(String token, String school) {
    // print("Enumeration school");
    // print(school);
    return http.post(
      Uri.parse('https://api.smarfe.sosit-wh.net/gamo-api/average_fields'),
      headers: <String, String>{
        'Content-Type': 'application/json; charset=UTF-8',
      },
      body: jsonEncode(<String, String>{'token': token, 'school': school}),
    );
  }

  Future<http.Response> getGraphValues(
      String token, String gateway, String nadr) {
    return http.post(
      Uri.parse('https://api.smarfe.sosit-wh.net/gamo-api/graph_data'),
      headers: <String, String>{
        'Content-Type': 'application/json; charset=UTF-8',
      },
      body: jsonEncode(
          <String, String>{'token': token, 'gateway': gateway, 'nadr': nadr}),
    );
  }

  Future<http.Response> getPDFValues(
      String token, String gateway, String nadr, String school) {

    return http.post(
      Uri.parse('https://api.smarfe.sosit-wh.net/gamo-api/summary'),
      headers: <String, String>{
        'Content-Type': 'application/json; charset=UTF-8',
      },
      body: jsonEncode(
          <String, String>{'token': token, 'gateway': gateway, 'nadr': nadr, 'school': school}),
    );
  }

}

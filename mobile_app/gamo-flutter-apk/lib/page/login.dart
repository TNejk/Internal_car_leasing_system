import 'dart:convert';
import 'dart:developer';
import 'package:flutter/material.dart';
import 'package:flutter_application_1/api/loginResult.dart';
import 'package:go_router/go_router.dart';
import 'package:hexcolor/hexcolor.dart';
import 'package:flutter_application_1/api/services.dart';

class LoginPage extends StatefulWidget {
  LoginPage({Key? key}) : super(key: key);

  @override
  _LoginPageState createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final nameBoxController = TextEditingController();
  final passBoxController = TextEditingController();

  Future<LoginResult> checkCredentials() async {
    var result = await Services().loginResult(nameBoxController.text, passBoxController.text);
    final data = await jsonDecode(result.body) as Map<String, dynamic>;
      print("*************************");
      print(data["status"]);
      log('your message here');
      log('$data');
      var object = LoginResult(connected: data["status"], json: data);

      return object;
  }

  @override
  Widget build(BuildContext context) {
    double width = MediaQuery.of(context).size.width;
    double height = MediaQuery.of(context).size.height;
    return Scaffold(
      resizeToAvoidBottomInset: false,
      backgroundColor: Colors.white,
      body: Padding(
        padding: EdgeInsets.only(left: 20.0, right: 20.0, bottom: height * 0.2),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.end,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: EdgeInsets.only(bottom: height * 0.1),
              child: Image.asset("assets/smarfe.png"),
            ),
            SizedBox(height: 20),
            Padding(
              padding: EdgeInsets.only(right: width * 0.05, left: width * 0.05),
              child: TextField(
                controller: nameBoxController,
                decoration: InputDecoration(
                  labelText: 'Username',
                  border: OutlineInputBorder(),
                ),
              ),
            ),
            SizedBox(height: 20),
            Padding(
              padding: EdgeInsets.only(left: width * 0.05, right: width * 0.05),
              child: TextField(
                controller: passBoxController,
                obscureText: true,
                decoration: InputDecoration(
                  labelText: 'Password',
                  border: OutlineInputBorder(),
                ),
              ),
            ),
            SizedBox(height: 20),
            Padding(
              padding: EdgeInsets.only(left: width * 0.05, right: width * 0.05),
              child: ElevatedButton(
                onPressed: () {
                  // Perform login action
                  // For now, let's just navigate to the home page
                  // Trigger the FutureBuilder by calling your async function
                  Future<LoginResult> futureResult = checkCredentials();

                  //? Create a new material page to display the loading sequence
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (context) => Scaffold(
                        backgroundColor: Color.fromARGB(255, 255, 255, 255),
                        appBar: AppBar(
                          backgroundColor: Colors.red[400],
                          iconTheme:
                              const IconThemeData(color: Color(0xffffffff)),
                          title: const Text(
                            "Login Result",
                            style: TextStyle(color: Color(0xffffffff)),
                          ),
                        ),
                        body: FutureBuilder<LoginResult>(
                          future: checkCredentials(),
                          builder: (context, snapshot) {
                            if (snapshot.connectionState ==
                                ConnectionState.waiting) {
                                  log('WAITING FutureBuilder snapshot: ${snapshot.data}');
                              return const Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                crossAxisAlignment: CrossAxisAlignment.center,
                                children: [
                                  Text("Signing in..."),
                                  SizedBox(
                                    height: 20,
                                  ),
                                  CircularProgressIndicator()
                                ],
                              );
                            } else {
                              // If done check credentials
                              if (snapshot.connectionState == ConnectionState.done) {
                                log('DONE FutureBuilder snapshot: ${snapshot.data}');
                                if (snapshot.data?.connected == "true") {
                                  //! If credentials are valid, navigate to the dashboard and give dashboard the token, and privlige
                                  //! The token is a connection token used for sending to the server whenever we want to get/post something
                          
                                  return AlertDialog(
                                    backgroundColor: Color.fromARGB(255, 41, 107, 131),
                                    title: const Text(
                                      'Logged in!',
                                      style: TextStyle(color: Color(0xffffffff)),
                                    ),
                                    actions: [
                                      TextButton(
                                        onPressed: () {
                                          context.goNamed("home");
                                          }, //Nvigator.popContext
                                        child: const Text('OK',
                                            style: TextStyle(
                                              color: Color(0xffffffff),
                                            )),
                                      ),
                                    ],
                                  );

                                } 
                                else {
                                  //! If credentials are not valid, show an AlertDialog
                              log('ERROR FutureBuilder snapshot: ${snapshot.data}');
                                  
                                  return AlertDialog(
                                    backgroundColor: Colors.red[400],
                                    title: const Text(
                                      'Incorrect name or password!',
                                      style: TextStyle(color: Color(0xffffffff)),
                                    ),
                                    actions: [
                                      TextButton(
                                        onPressed: () {
                                          Navigator.pop(context);
                                          }, //Nvigator.popContext
                                        child: const Text('OK',
                                            style: TextStyle(
                                              color: Color(0xffffffff),
                                            )),
                                      ),
                                    ],
                                  );
                                }
                              }
                            }
                            //
                            return Text(
                                "Internal error plesae contact the administrators.");
                          },
                        ),
                      ),
                    ),
                  );
                },
                child: Text(
                  'Login',
                  style: TextStyle(color: Colors.black),
                ),
              ),
            ),
            SizedBox(height: 10),
            TextButton(
              onPressed: () {},
              child: Text('Forgot Password?'),
            ),
          ],
        ),
      ),
      bottomSheet: Container(
        height: 30,
        color: Colors.grey[200],
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Padding(
              padding: EdgeInsets.only(left: 10),
              child: Text("SOS IT, BB"),
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

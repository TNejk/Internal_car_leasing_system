import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_application_1/api/firebase_api.dart';
import 'package:flutter_application_1/page/home.dart';
import 'package:flutter_application_1/page/login.dart';
import 'package:flutter_application_1/page/notifications.dart';
import 'package:flutter_application_1/page/room.dart';
import 'package:flutter_application_1/page/senzorList.dart';
import 'firebase_options.dart';
import 'package:go_router/go_router.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  await FireBaseApi().initNotifications();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Flutter Demo',
      theme: ThemeData(
        useMaterial3: true,
      ),
      debugShowCheckedModeBanner: false,
      routerConfig: _router,
    );
  }
}

//
//
//
final GoRouter _router = GoRouter(initialLocation: "/", routes: [
    
    GoRoute(
      name: "login",
      path: "/",
      builder: ((context, state) => LoginPage()),
    ),
      //! DONT FORGET TO PUSH QUERY PARAMETERS TO THE PARENTS PAGE
      // Login has to be separate, dont put home in the logins route!!!
     
    GoRoute(
          name: "home",
          path: "/home",
          builder: (context, state) => HomeScreen(),
          routes: [
            GoRoute(
                  name: "room",
                  path: "room",
                  builder: ((context, state) => Room(
                    roomName: state.uri.queryParameters["roomName"]!,
                    gateway: state.uri.queryParameters["gateway"]!,
                    token: state.uri.queryParameters["token"]!,
                    nadr: state.uri.queryParameters["nadr"]!)),
            ),
            GoRoute(
                  name: "notifications",
                  path: "notifications",
                  builder: ((context, state) => NotificationPage()),
            ),
            GoRoute(
                  name: "senzors",
                  path: "senzors",
                  builder: ((context, state) => SenzorList(
                    token: state.uri.queryParameters["token"]!,
                  )),
            ),
          ]
        ),
]);

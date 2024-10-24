import 'dart:convert';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_application_1/main.dart';
import 'package:flutter_application_1/page/room.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

Future<void> handleBackroundMessage(RemoteMessage message) async {
  print("Title: ${message.notification?.title}");
  print("Title: ${message.notification?.body}");
  print("Title: ${message.data}");
}

class FireBaseApi {
  final _firebaseMessaging = FirebaseMessaging.instance;

  //! Android channel
  // Notification category for local notifications
  final _androidChannel = const AndroidNotificationChannel(
      "high_importance_channel", "High Importance Notifications",
      description: "This channel is used for important notifications",
      importance: Importance.defaultImportance);

  final _localNotifications = FlutterLocalNotificationsPlugin();

  // Route to a page the notification mentions
  // TODO: Route to a senzor page whenewer the user clicks
  // TODO: The senzor page will change depeding on the place we want
  void handleMessage(RemoteMessage? message) {
    if (message == null) return;
    //else navigate
  }

  Future initLocalNotifications() async {
    const IOS = DarwinInitializationSettings();
    const android = AndroidInitializationSettings("@drawable/ic_launcher.png");
    const settings = InitializationSettings(android: android, iOS: IOS);

    await _localNotifications.initialize(settings,
        onDidReceiveNotificationResponse: (payload) {
      // Decode the message without a null check and then
      final message =
          jsonDecode(payload.payload!); // Extract and decode the payload
      handleMessage(RemoteMessage.fromMap(message));
    });

    final platform = _localNotifications.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    await platform?.createNotificationChannel(_androidChannel);
  }

  Future initPushNotifications() async {
    // Configure notification settings
    await FirebaseMessaging.instance
        .setForegroundNotificationPresentationOptions(
            alert: true, badge: true, sound: false);

    try {
      await FirebaseMessaging.instance.subscribeToTopic('Users');
      print('subscribed to topic');
    } catch (e) {
      print('error is $e');
    }

    ////FirebaseMessaging.instance.getInitialMessage().then(handleMessage);
    // L istens for events where a user taps on a notification that was sent via FCM while the app is already open in the foreground or background
    FirebaseMessaging.onMessageOpenedApp.listen(handleMessage);
    // Backround notifications
    FirebaseMessaging.onBackgroundMessage(handleBackroundMessage);
    // Foreground Local Notifications
    FirebaseMessaging.onMessage.listen((message) {
      final notification = message.notification;
      if (notification == null) return;
      // Config for a local notification
      _localNotifications.show(
          notification.hashCode,
          notification.title,
          notification.body,
          NotificationDetails(
            android: AndroidNotificationDetails(
                _androidChannel.id, _androidChannel.name,
                channelDescription: _androidChannel.description,
                icon: "@drawable/ic_launcher"),
          ),
          payload: jsonEncode(message.toMap()));
    });
  }

  Future<void> initNotifications() async {
    // Initialize all types of notificatons
    await _firebaseMessaging.requestPermission();
    final fCMToken = await _firebaseMessaging.getToken();
    print(fCMToken);
    initPushNotifications();
    initLocalNotifications();
  }
}

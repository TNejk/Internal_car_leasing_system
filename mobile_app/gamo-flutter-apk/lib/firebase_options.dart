// File generated by FlutterFire CLI.
// ignore_for_file: lines_longer_than_80_chars, avoid_classes_with_only_static_members
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

/// Default [FirebaseOptions] for use with your Firebase apps.
///
/// Example:
/// ```dart
/// import 'firebase_options.dart';
/// // ...
/// await Firebase.initializeApp(
///   options: DefaultFirebaseOptions.currentPlatform,
/// );
/// ```
class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      return web;
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      case TargetPlatform.macOS:
        return macos;
      case TargetPlatform.windows:
        throw UnsupportedError(
          'DefaultFirebaseOptions have not been configured for windows - '
          'you can reconfigure this by running the FlutterFire CLI again.',
        );
      case TargetPlatform.linux:
        throw UnsupportedError(
          'DefaultFirebaseOptions have not been configured for linux - '
          'you can reconfigure this by running the FlutterFire CLI again.',
        );
      default:
        throw UnsupportedError(
          'DefaultFirebaseOptions are not supported for this platform.',
        );
    }
  }

  static const FirebaseOptions web = FirebaseOptions(
    apiKey: 'AIzaSyBTFH38vhvXoCpFAbeXij28Hslmhx-j1KI',
    appId: '1:867098986517:web:edb36db4c1dba73863661c',
    messagingSenderId: '867098986517',
    projectId: 'aklsdjlaksjal',
    authDomain: 'aklsdjlaksjal.firebaseapp.com',
    storageBucket: 'aklsdjlaksjal.appspot.com',
  );

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyA-tE-emHOEJhBLiQ8w42h0VhwNY0TEwJg',
    appId: '1:867098986517:android:e75b1225768de65963661c',
    messagingSenderId: '867098986517',
    projectId: 'aklsdjlaksjal',
    storageBucket: 'aklsdjlaksjal.appspot.com',
  );

  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: 'AIzaSyDNcr3Fvxqr4DeILM9HFE1M5vXLj_W-V3s',
    appId: '1:867098986517:ios:1c34c3627b508a0963661c',
    messagingSenderId: '867098986517',
    projectId: 'aklsdjlaksjal',
    storageBucket: 'aklsdjlaksjal.appspot.com',
    iosBundleId: 'com.example.flutterApplication1',
  );

  static const FirebaseOptions macos = FirebaseOptions(
    apiKey: 'AIzaSyDNcr3Fvxqr4DeILM9HFE1M5vXLj_W-V3s',
    appId: '1:867098986517:ios:6831ed13b387400063661c',
    messagingSenderId: '867098986517',
    projectId: 'aklsdjlaksjal',
    storageBucket: 'aklsdjlaksjal.appspot.com',
    iosBundleId: 'com.example.flutterApplication1.RunnerTests',
  );
}

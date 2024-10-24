//class for the loginPage authentication function, its standard to map clasess to json returns
class LoginResult {
  final String connected;
  final Map<String, dynamic> json;
  LoginResult({required this.connected, required this.json});
}

import 'package:flutter_test/flutter_test.dart';
import 'package:arena360/main.dart';

void main() {
  testWidgets('ARENA 360 opens the Mongolian sign-in screen', (tester) async {
    await tester.pumpWidget(const Arena360App());

    expect(find.text('ARENA 360'), findsOneWidget);
    expect(find.text('Нэвтрэх'), findsOneWidget);
    expect(find.text('Утасны дугаар'), findsOneWidget);
  });
}

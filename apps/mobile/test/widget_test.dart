import 'package:flutter_test/flutter_test.dart';
import 'package:arena360/main.dart';

void main() {
  testWidgets('ARENA 360 app displays the authentication screen', (tester) async {
    await tester.pumpWidget(const Arena360App());
    expect(find.text('ARENA 360'), findsOneWidget);
    expect(find.text('ONE PLATFORM. ALL SPORTS.'), findsOneWidget);
    expect(find.text('Нэвтрэх'), findsOneWidget);
  });
}

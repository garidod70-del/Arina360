import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:arena360/main.dart';

void main() {
  testWidgets('ARINA 360 app displays the authentication screen', (tester) async {
    await tester.pumpWidget(const Arena360App());
    expect(
      find.byWidgetPredicate(
        (widget) => widget is RichText && widget.text.toPlainText() == 'ARINA 360',
      ),
      findsOneWidget,
    );
    expect(find.text('SPORT • CONNECT • GROW'), findsOneWidget);
    expect(find.text('Нэвтрэх'), findsOneWidget);
  });

  testWidgets('login does not enter a demo session without an API endpoint', (tester) async {
    tester.view.physicalSize = const Size(1080, 1920);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const Arena360App());
    await tester.enterText(find.byType(TextFormField).at(0), '99112233');
    await tester.enterText(find.byType(TextFormField).at(1), 'secure-test-password');
    await tester.tap(find.text('НЭВТРЭХ'));
    await tester.pump();

    expect(find.textContaining('Серверийн хаяг тохируулаагүй байна'), findsOneWidget);
    expect(find.text('ONE PLATFORM. ALL SPORTS.'), findsNothing);
    expect(find.text('Нэвтрэх'), findsOneWidget);
  });
}

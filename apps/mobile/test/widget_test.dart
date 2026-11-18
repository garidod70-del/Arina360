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
}

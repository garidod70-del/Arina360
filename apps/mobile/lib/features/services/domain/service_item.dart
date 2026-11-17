import 'package:flutter/material.dart';

class ServiceItem {
  final IconData icon;
  final String name;
  final String description;

  const ServiceItem(this.icon, this.name, this.description);
}

const services = <ServiceItem>[
  ServiceItem(Icons.sports, 'Шүүгч', 'Шүүгч хайх, зэрэглэл болон тэмцээний захиалга'),
  ServiceItem(Icons.sports_martial_arts, 'Дасгалжуулагч', 'Спортын дасгалжуулагч, хувийн болон багийн бэлтгэл'),
  ServiceItem(Icons.medical_services, 'Спортын эмч', 'Спортын эмчийн зөвлөгөө, үзлэгийн цаг'),
  ServiceItem(Icons.fitness_center, 'Хүчний мэргэжилтэн', 'Хүч, хурд, тэсрэлттэй хүчний бэлтгэл'),
  ServiceItem(Icons.psychology, 'Сэтгэл зүйч', 'Тамирчны сэтгэл зүйн зөвлөгөө, бэлтгэл'),
  ServiceItem(Icons.restaurant, 'Хоол зүйч', 'Тамирчны хооллолт, жингийн зохицуулалт'),
  ServiceItem(Icons.accessibility_new, 'Хөдөлгөөн засалч', 'Нөхөн сэргээх болон хөдөлгөөн засах үйлчилгээ'),
  ServiceItem(Icons.analytics, 'Спортын шинжээч', 'Тамирчны үзүүлэлт, тэмцээний статистик'),
  ServiceItem(Icons.stadium, 'Заал захиалга', 'Заал, талбай хайх болон цаг захиалах'),
  ServiceItem(Icons.shopping_bag, 'Спорт бараа худалдаа', 'Спортын хувцас, хэрэгсэл, захиалга'),
  ServiceItem(Icons.groups, 'Сургалт, клубууд', 'Клуб, секц, сургалтын элсэлт ба хуваарь'),
];

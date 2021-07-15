CREATE DATABASE devnet_dashboards;

CREATE TABLE `inventory` (
  `hostname` varchar(45) DEFAULT NULL,
  `mgmt_ip_address` varchar(45) NOT NULL,
  `serial_number` varchar(30) DEFAULT NULL,
  `device_type` varchar(120) DEFAULT NULL,
  `device_group` varchar(45) DEFAULT NULL,
  `model` varchar(45) DEFAULT NULL,
  `source` varchar(30) DEFAULT NULL,
  `software_version` varchar(30) DEFAULT NULL,
  `location` varchar(60) DEFAULT NULL,
  `contacts` varchar(255) DEFAULT NULL,
  `do_ping` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`mgmt_ip_address`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci

CREATE TABLE `pingresults` (
  `mgmt_ip_address` varchar(45) NOT NULL,
  `reachable_pct` tinyint DEFAULT NULL,
  `avg_latency` decimal(7,2) DEFAULT NULL,
  `min_latency` decimal(7,2) DEFAULT NULL,
  `max_latency` decimal(7,2) DEFAULT NULL,
  `datetime_lastup` datetime DEFAULT NULL,
  `down_count` int NOT NULL,
  PRIMARY KEY (`mgmt_ip_address`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci


CREATE USER 'dddbu'@'localhost' IDENTIFIED BY '###PASSWORD###';

GRANT ALL PRIVILEGES ON devnet_dashboards . * TO 'dddbu'@'localhost';

-- Create the database
CREATE DATABASE IF NOT EXISTS `weight`;
USE `weight`;

-- Create containers_registered table
CREATE TABLE IF NOT EXISTS `containers_registered` (
  `container_id` VARCHAR(15) NOT NULL,
  `weight` INT(12) DEFAULT NULL,
  `unit` VARCHAR(10) DEFAULT NULL,
  PRIMARY KEY (`container_id`)
) ENGINE=InnoDB;

-- Create transactions table
CREATE TABLE IF NOT EXISTS `transactions` (
  `id` INT(12) NOT NULL AUTO_INCREMENT,  -- session/ transaction id
  `datetime` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `direction` VARCHAR(10) DEFAULT NULL,  -- in/ out
  `truck` VARCHAR(50) DEFAULT NULL, -- truck id
  `containers` VARCHAR(10000) DEFAULT NULL, -- container id
  `bruto` INT(12) DEFAULT NULL,
  `truckTara` INT(12) DEFAULT NULL,
  `neto` INT(12) DEFAULT NULL,
  `produce` VARCHAR(50) DEFAULT NULL, -- produce type
  PRIMARY KEY (`id`)
) ENGINE=InnoDB;

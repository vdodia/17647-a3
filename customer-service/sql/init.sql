-- Customers database schema initialization

CREATE TABLE IF NOT EXISTS customers (
    id          INT             AUTO_INCREMENT PRIMARY KEY,
    userId      VARCHAR(255)    UNIQUE NOT NULL,
    name        VARCHAR(255)    NOT NULL,
    phone       VARCHAR(50)     NOT NULL,
    address     VARCHAR(255)    NOT NULL,
    address2    VARCHAR(255),
    city        VARCHAR(100)    NOT NULL,
    state       CHAR(2)         NOT NULL,
    zipcode     VARCHAR(10)     NOT NULL
);

-- VietinCare AI - MySQL Community Server 8.0.46
-- Khoi tao tren database moi. Khong xoa bang hoac du lieu da co.
-- Tat ca ket noi backend can dung utf8mb4 va time_zone = '+00:00'.
SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci;
SET SESSION time_zone = '+00:00';
CREATE DATABASE IF NOT EXISTS QLKHViettin
    CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

USE QLKHViettin;
SELECT DATABASE() AS CurrentDatabase;

CREATE TABLE `Customer` (
    MaKH INT AUTO_INCREMENT PRIMARY KEY,
    HoTen VARCHAR(100) NOT NULL,
    Email VARCHAR(100),
    SoDienThoai VARCHAR(20),
    LoaiKhachHang VARCHAR(20),
    NgayTao DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    TrangThai BOOLEAN DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `Role` (
    MaRole INT AUTO_INCREMENT PRIMARY KEY,
    TenRole VARCHAR(50) NOT NULL UNIQUE,
    MoTa VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `UserAccount` (
    MaUser INT AUTO_INCREMENT PRIMARY KEY,
    MaRole INT NOT NULL,
    HoTen VARCHAR(100) NOT NULL,
    Username VARCHAR(50) NOT NULL UNIQUE,
    PasswordHash VARCHAR(255) NOT NULL,
    Email VARCHAR(100),
    SoDienThoai VARCHAR(20),
    TrangThai BOOLEAN DEFAULT 1,
    NgayTao DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT FK_UserAccount_Role
        FOREIGN KEY (MaRole)
        REFERENCES `Role`(MaRole)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `ChatSession` (
    MaSession INT AUTO_INCREMENT PRIMARY KEY,
    MaKH INT NOT NULL,
    MaAgent INT NULL,
    ThoiGianBatDau DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    ThoiGianKetThuc DATETIME(3) NULL,
    KenhChat VARCHAR(50),
    TrangThai VARCHAR(30) DEFAULT 'Đang hoạt động',

    CONSTRAINT FK_ChatSession_Customer
        FOREIGN KEY (MaKH)
        REFERENCES `Customer`(MaKH),

    CONSTRAINT FK_ChatSession_Agent
        FOREIGN KEY (MaAgent)
        REFERENCES `UserAccount`(MaUser)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `Message` (
    MaMessage INT AUTO_INCREMENT PRIMARY KEY,
    MaSession INT NOT NULL,
    NguoiGui VARCHAR(20) NOT NULL,
    NoiDung LONGTEXT NOT NULL,
    ThoiGian DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    DoTinCayAI DECIMAL(5,2) NULL,

    CONSTRAINT FK_Message_ChatSession
        FOREIGN KEY (MaSession)
        REFERENCES `ChatSession`(MaSession)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `TicketCategory` (
    MaCategory INT AUTO_INCREMENT PRIMARY KEY,
    TenCategory VARCHAR(100) NOT NULL,
    MoTa VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `Ticket` (
    MaTicket INT AUTO_INCREMENT PRIMARY KEY,
    MaKH INT NOT NULL,
    MaSession INT NULL,
    MaCategory INT NULL,
    MaAgent INT NULL,

    TieuDe VARCHAR(200) NOT NULL,
    NoiDung LONGTEXT NOT NULL,

    MucDoUuTien VARCHAR(30) DEFAULT 'Trung bình',
    TrangThai VARCHAR(30) DEFAULT 'Mới',

    NgayTao DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    NgayCapNhat DATETIME(3) NULL,
    NgayDong DATETIME(3) NULL,

    CONSTRAINT FK_Ticket_Customer
        FOREIGN KEY (MaKH)
        REFERENCES `Customer`(MaKH),

    CONSTRAINT FK_Ticket_ChatSession
        FOREIGN KEY (MaSession)
        REFERENCES `ChatSession`(MaSession),

    CONSTRAINT FK_Ticket_Category
        FOREIGN KEY (MaCategory)
        REFERENCES `TicketCategory`(MaCategory),

    CONSTRAINT FK_Ticket_Agent
        FOREIGN KEY (MaAgent)
        REFERENCES `UserAccount`(MaUser)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `Handover` (
    MaHandover INT AUTO_INCREMENT PRIMARY KEY,
    MaSession INT NOT NULL,
    MaAgent INT NULL,
    LyDo VARCHAR(255),
    ThoiGian DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    TrangThai VARCHAR(30) DEFAULT 'Chờ tiếp nhận',

    CONSTRAINT FK_Handover_Session
        FOREIGN KEY (MaSession)
        REFERENCES `ChatSession`(MaSession),

    CONSTRAINT FK_Handover_Agent
        FOREIGN KEY (MaAgent)
        REFERENCES `UserAccount`(MaUser)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `SentimentAnalysis` (
    MaSentiment INT AUTO_INCREMENT PRIMARY KEY,
    MaMessage INT NOT NULL,
    CamXuc VARCHAR(30) NOT NULL,
    DiemCamXuc DECIMAL(5,2),
    ThoiGian DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT FK_Sentiment_Message
        FOREIGN KEY (MaMessage)
        REFERENCES `Message`(MaMessage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `AISuggestion` (
    MaSuggestion INT AUTO_INCREMENT PRIMARY KEY,
    MaMessage INT NOT NULL,
    NoiDungGoiY LONGTEXT NOT NULL,
    DoTinCay DECIMAL(5,2),
    DuocChon BOOLEAN DEFAULT 0,
    ThoiGian DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT FK_AISuggestion_Message
        FOREIGN KEY (MaMessage)
        REFERENCES `Message`(MaMessage)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `ConversationSummary` (
    MaSummary INT AUTO_INCREMENT PRIMARY KEY,
    MaSession INT NOT NULL,
    NoiDungTomTat LONGTEXT NOT NULL,
    ThoiGianTao DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT FK_Summary_Session
        FOREIGN KEY (MaSession)
        REFERENCES `ChatSession`(MaSession)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `Evaluation` (
    MaDanhGia INT AUTO_INCREMENT PRIMARY KEY,
    MaKH INT NOT NULL,
    MaSession INT NULL,
    MaTicket INT NULL,

    SoSao INT CHECK (SoSao BETWEEN 1 AND 5),
    NhanXet VARCHAR(1000),
    DiemNPS INT NULL,
    NgayDanhGia DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT FK_Evaluation_Customer
        FOREIGN KEY (MaKH)
        REFERENCES `Customer`(MaKH),

    CONSTRAINT FK_Evaluation_Session
        FOREIGN KEY (MaSession)
        REFERENCES `ChatSession`(MaSession),

    CONSTRAINT FK_Evaluation_Ticket
        FOREIGN KEY (MaTicket)
        REFERENCES `Ticket`(MaTicket)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `KnowledgeBase` (
    MaKB INT AUTO_INCREMENT PRIMARY KEY,
    MaUser INT NOT NULL,
    TieuDe VARCHAR(200) NOT NULL,
    NoiDung LONGTEXT,
    LoaiTaiLieu VARCHAR(50),
    TrangThai VARCHAR(30) DEFAULT 'Nháp',
    NgayTao DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    NgayCapNhat DATETIME(3) NULL,

    CONSTRAINT FK_KnowledgeBase_User
        FOREIGN KEY (MaUser)
        REFERENCES `UserAccount`(MaUser)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
CREATE TABLE `AuditLog` (
    MaLog INT AUTO_INCREMENT PRIMARY KEY,
    MaUser INT NULL,
    HanhDong VARCHAR(100) NOT NULL,
    DoiTuong VARCHAR(100),
    MaDoiTuong INT NULL,
    DiaChiIP VARCHAR(50),
    ThoiGian DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    ChiTiet LONGTEXT,

    CONSTRAINT FK_AuditLog_User
        FOREIGN KEY (MaUser)
        REFERENCES `UserAccount`(MaUser)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
-- Cac doan tri thuc cho RAG chi luu trong MySQL.
-- Backend tao embedding va tinh cosine similarity, khong dung database rieng.
CREATE TABLE `KnowledgeChunk` (
    MaChunk INT AUTO_INCREMENT PRIMARY KEY,
    MaKB INT NOT NULL,
    ThuTu INT NOT NULL,
    NoiDung LONGTEXT NOT NULL,
    Embedding JSON NULL,
    TenMoHinh VARCHAR(100) NULL,
    SoChieu INT NULL,
    NgayTao DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    CONSTRAINT UQ_KnowledgeChunk_Order UNIQUE (MaKB, ThuTu),
    CONSTRAINT FK_KnowledgeChunk_KnowledgeBase
        FOREIGN KEY (MaKB) REFERENCES `KnowledgeBase`(MaKB),
    CONSTRAINT CK_KnowledgeChunk_Order CHECK (ThuTu >= 0),
    CONSTRAINT CK_KnowledgeChunk_Embedding CHECK (
        (Embedding IS NULL AND SoChieu IS NULL AND TenMoHinh IS NULL)
        OR
        (Embedding IS NOT NULL AND SoChieu IS NOT NULL AND TenMoHinh IS NOT NULL
         AND SoChieu > 0 AND JSON_TYPE(Embedding) = 'ARRAY'
         AND JSON_LENGTH(Embedding) = SoChieu)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;
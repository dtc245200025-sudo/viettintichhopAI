-- Preserve existing conversations and messages. Runtime only needs CRUD grants.
ALTER TABLE ChatSession ADD COLUMN TieuDe VARCHAR(200) NULL, ADD INDEX IX_ChatSession_CustomerId(MaKH,MaSession);
ALTER TABLE Message ADD INDEX IX_Message_SessionId(MaSession,MaMessage);
CREATE TABLE ChatRequest (MaUser INT NOT NULL, RequestKey CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, RequestHash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, Result JSON NOT NULL, CreatedAt DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3), PRIMARY KEY(MaUser,RequestKey), CONSTRAINT FK_ChatRequest_User FOREIGN KEY(MaUser) REFERENCES UserAccount(MaUser)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

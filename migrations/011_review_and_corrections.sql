-- Append-only corrections preserve the original interaction and its author.
ALTER TABLE TicketReply ADD COLUMN CorrectionOf INT NULL, ADD CONSTRAINT FK_Reply_Correction FOREIGN KEY(CorrectionOf) REFERENCES TicketReply(MaReply);
ALTER TABLE Message ADD COLUMN CorrectionOf INT NULL, ADD CONSTRAINT FK_Message_Correction FOREIGN KEY(CorrectionOf) REFERENCES Message(MaMessage);
INSERT INTO SystemSetting(SettingKey,SettingValue,ValueType) VALUES('auth.session_hours','8','integer') ON DUPLICATE KEY UPDATE SettingKey=VALUES(SettingKey);

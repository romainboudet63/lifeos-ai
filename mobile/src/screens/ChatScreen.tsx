import React, { useCallback, useRef, useState } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useTheme } from "../theme/useTheme";
import { typography, spacing, radius } from "../theme/typography";
import { chatApi } from "../api/endpoints";
import { ChatMessage } from "../api/types";
import { Input } from "../components/Input";
import { Button } from "../components/Button";

export function ChatScreen() {
  const { colors } = useTheme();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const listRef = useRef<FlatList>(null);

  const load = useCallback(async () => {
    setMessages(await chatApi.history());
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text, created_at: new Date().toISOString() }]);
    setSending(true);
    try {
      const res = await chatApi.send(text);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply, created_at: new Date().toISOString() }]);
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100);
    } finally {
      setSending(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: colors.background }]}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={90}
    >
      <Text style={[typography.title, { color: colors.textPrimary, margin: spacing.lg, marginBottom: spacing.sm }]}>
        Assistant
      </Text>

      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(_, i) => String(i)}
        contentContainerStyle={{ padding: spacing.lg, paddingTop: 0, flexGrow: 1 }}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: false })}
        ListEmptyComponent={
          <Text style={[typography.body, { color: colors.textSecondary }]}>
            Pose une question à ton assistant — il connaît tes tâches, habitudes et objectifs.
          </Text>
        }
        renderItem={({ item }) => (
          <View
            style={[
              styles.bubble,
              item.role === "user"
                ? { alignSelf: "flex-end", backgroundColor: colors.accent }
                : { alignSelf: "flex-start", backgroundColor: colors.surfaceMuted },
            ]}
          >
            <Text style={[typography.body, { color: item.role === "user" ? colors.textInverse : colors.textPrimary }]}>
              {item.content}
            </Text>
          </View>
        )}
      />

      <View style={styles.inputRow}>
        <View style={{ flex: 1 }}>
          <Input
            value={input}
            onChangeText={setInput}
            placeholder="Écris un message..."
            onSubmitEditing={handleSend}
            style={{ marginBottom: 0 }}
          />
        </View>
        <Button label="Envoyer" onPress={handleSend} loading={sending} disabled={!input.trim()} style={styles.sendButton} />
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  bubble: { maxWidth: "80%", padding: spacing.sm + 4, borderRadius: radius.md, marginBottom: spacing.sm },
  inputRow: { flexDirection: "row", alignItems: "flex-start", paddingHorizontal: spacing.lg, paddingBottom: spacing.md, gap: spacing.sm },
  sendButton: { paddingHorizontal: spacing.md },
});

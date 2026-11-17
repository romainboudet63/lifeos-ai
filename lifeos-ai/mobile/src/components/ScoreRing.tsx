import React from "react";
import { View, Text, StyleSheet } from "react-native";
import Svg, { Circle } from "react-native-svg";
import { useTheme } from "../theme/useTheme";
import { typography } from "../theme/typography";

interface ScoreRingProps {
  score: number; // 0-100
  size?: number;
  label?: string;
}

/**
 * Élément signature de LifeOS : un anneau de progression qui évoque un
 * cerne de croissance (arbre) plutôt qu'une jauge de chargement générique
 * — cohérent avec la thématique "croissance personnelle" de l'app.
 */
export function ScoreRing({ score, size = 160, label = "Daily Life Score" }: ScoreRingProps) {
  const { colors } = useTheme();
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.max(0, Math.min(100, score)) / 100;
  const dashOffset = circumference * (1 - progress);

  return (
    <View style={{ width: size, height: size, alignItems: "center", justifyContent: "center" }}>
      <Svg width={size} height={size}>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={colors.scoreRingTrack}
          strokeWidth={strokeWidth}
          fill="none"
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={colors.accent}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          rotation={-90}
          origin={`${size / 2}, ${size / 2}`}
        />
      </Svg>
      <View style={StyleSheet.absoluteFill}>
        <View style={styles.centerContent}>
          <Text style={[typography.display, { color: colors.textPrimary }]}>{Math.round(score)}</Text>
          <Text style={[typography.label, { color: colors.textSecondary, marginTop: 2 }]}>
            {label.toUpperCase()}
          </Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  centerContent: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
});

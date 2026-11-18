import React from "react";
import { View, Text, StyleSheet } from "react-native";
import Svg, { Circle } from "react-native-svg";
import { useTheme } from "../theme/useTheme";
import { typography, spacing } from "../theme/typography";

interface CategorySlice {
  category: string;
  total: number;
}

interface SpendingDonutProps {
  data: CategorySlice[];
  size?: number;
}

// Palette dédiée aux graphiques — distincte des tokens de thème globaux
// (qui n'ont qu'une couleur d'accent), pour distinguer plusieurs
// catégories tout en restant dans l'univers "croissance personnelle"
// de l'app plutôt que des couleurs de dataviz génériques.
const CHART_PALETTE = [
  "#3F7A5C", // mousse
  "#C98A3D", // ambre
  "#6E7DAB", // bleu poussière
  "#B4523F", // argile
  "#8C6BAE", // prune
  "#4FA3A0", // sarcelle
  "#A6763F", // bronze
];

function formatEuros(amount: number): string {
  return `${amount.toLocaleString("fr-FR", { maximumFractionDigits: 0 })}€`;
}

/**
 * Anneau multi-segments : même technique que ScoreRing (strokeDasharray
 * + rotation) mais avec plusieurs Circle empilés, un par catégorie,
 * décalés cumulativement pour former les segments d'un donut.
 */
export function SpendingDonut({ data, size = 180 }: SpendingDonutProps) {
  const { colors } = useTheme();
  const strokeWidth = 22;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const total = data.reduce((sum, d) => sum + d.total, 0);

  if (total <= 0) {
    return (
      <View style={[styles.emptyState, { width: size, height: size }]}>
        <Text style={[typography.caption, { color: colors.textSecondary, textAlign: "center" }]}>
          Aucune dépense ce mois-ci
        </Text>
      </View>
    );
  }

  let cumulativeFraction = 0;

  return (
    <View style={styles.wrapper}>
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
          {data.map((slice, index) => {
            const fraction = slice.total / total;
            const arcLength = circumference * fraction;
            const offset = circumference * cumulativeFraction;
            cumulativeFraction += fraction;

            return (
              <Circle
                key={slice.category}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                stroke={CHART_PALETTE[index % CHART_PALETTE.length]}
                strokeWidth={strokeWidth}
                fill="none"
                strokeDasharray={`${arcLength} ${circumference - arcLength}`}
                strokeDashoffset={-offset}
                rotation={-90}
                origin={`${size / 2}, ${size / 2}`}
              />
            );
          })}
        </Svg>
        <View style={StyleSheet.absoluteFill}>
          <View style={styles.centerContent}>
            <Text style={[typography.title, { color: colors.textPrimary }]}>{formatEuros(total)}</Text>
            <Text style={[typography.label, { color: colors.textSecondary, marginTop: 2 }]}>CE MOIS-CI</Text>
          </View>
        </View>
      </View>

      <View style={styles.legend}>
        {data.map((slice, index) => (
          <View key={slice.category} style={styles.legendRow}>
            <View style={[styles.legendDot, { backgroundColor: CHART_PALETTE[index % CHART_PALETTE.length] }]} />
            <Text style={[typography.body, { color: colors.textPrimary, flex: 1 }]}>{slice.category}</Text>
            <Text style={[typography.bodyStrong, { color: colors.textSecondary }]}>{formatEuros(slice.total)}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { alignItems: "center" },
  centerContent: { flex: 1, alignItems: "center", justifyContent: "center" },
  emptyState: { alignItems: "center", justifyContent: "center" },
  legend: { width: "100%", marginTop: spacing.md },
  legendRow: { flexDirection: "row", alignItems: "center", paddingVertical: spacing.xs, gap: spacing.sm },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
});

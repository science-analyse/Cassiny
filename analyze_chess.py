#!/usr/bin/env python3
"""
Chess Performance Analysis Script
Analyzes Lichess PGN data to provide insights for chess improvement
"""

import re
from collections import defaultdict, Counter
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path

# Set style for better-looking charts
sns.set_style("darkgrid")
sns.set_palette("husl")

class ChessAnalyzer:
    def __init__(self, pgn_file):
        self.pgn_file = pgn_file
        self.games = []
        self.username = "Cassiny"

    def parse_pgn(self):
        """Parse PGN file and extract game data"""
        print(f"Parsing {self.pgn_file}...")

        with open(self.pgn_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split by games
        game_texts = re.split(r'\n\n\[Event', content)

        for i, game_text in enumerate(game_texts):
            if i == 0:
                game_text = game_text
            else:
                game_text = '[Event' + game_text

            if not game_text.strip():
                continue

            game_data = self.parse_game(game_text)
            if game_data:
                self.games.append(game_data)

        print(f"Parsed {len(self.games)} games successfully")
        return self.games

    def parse_game(self, game_text):
        """Parse individual game"""
        try:
            game = {}

            # Extract metadata using regex
            patterns = {
                'event': r'\[Event "([^"]+)"\]',
                'date': r'\[UTCDate "([^"]+)"\]',
                'white': r'\[White "([^"]+)"\]',
                'black': r'\[Black "([^"]+)"\]',
                'result': r'\[Result "([^"]+)"\]',
                'white_elo': r'\[WhiteElo "([^"]+)"\]',
                'black_elo': r'\[BlackElo "([^"]+)"\]',
                'white_rating_diff': r'\[WhiteRatingDiff "([^"]+)"\]',
                'black_rating_diff': r'\[BlackRatingDiff "([^"]+)"\]',
                'time_control': r'\[TimeControl "([^"]+)"\]',
                'eco': r'\[ECO "([^"]+)"\]',
                'opening': r'\[Opening "([^"]+)"\]',
                'termination': r'\[Termination "([^"]+)"\]',
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, game_text)
                if match:
                    game[key] = match.group(1)
                else:
                    game[key] = None

            # Determine player color and outcome
            if game['white'] == self.username:
                game['my_color'] = 'white'
                game['my_elo'] = game['white_elo']
                game['opp_elo'] = game['black_elo']
                game['rating_diff'] = game['white_rating_diff']

                if game['result'] == '1-0':
                    game['outcome'] = 'win'
                elif game['result'] == '0-1':
                    game['outcome'] = 'loss'
                else:
                    game['outcome'] = 'draw'

            elif game['black'] == self.username:
                game['my_color'] = 'black'
                game['my_elo'] = game['black_elo']
                game['opp_elo'] = game['white_elo']
                game['rating_diff'] = game['black_rating_diff']

                if game['result'] == '0-1':
                    game['outcome'] = 'win'
                elif game['result'] == '1-0':
                    game['outcome'] = 'loss'
                else:
                    game['outcome'] = 'draw'
            else:
                return None

            # Convert numeric fields
            if game['my_elo']:
                game['my_elo'] = int(game['my_elo'])
            if game['opp_elo']:
                game['opp_elo'] = int(game['opp_elo'])
            if game['rating_diff']:
                game['rating_diff'] = int(game['rating_diff'])

            # Parse date
            if game['date']:
                try:
                    game['datetime'] = datetime.strptime(game['date'], '%Y.%m.%d')
                except:
                    game['datetime'] = None

            # Categorize time control
            if game['time_control'] and game['time_control'] != '-':
                tc_parts = game['time_control'].split('+')
                if len(tc_parts) >= 1:
                    base_time = int(tc_parts[0])
                    if base_time < 180:
                        game['time_category'] = 'bullet'
                    elif base_time < 480:
                        game['time_category'] = 'blitz'
                    elif base_time < 1500:
                        game['time_category'] = 'rapid'
                    else:
                        game['time_category'] = 'classical'
                else:
                    game['time_category'] = 'unknown'
            else:
                game['time_category'] = 'unknown'

            return game

        except Exception as e:
            print(f"Error parsing game: {e}")
            return None

    def get_statistics(self):
        """Calculate key statistics"""
        df = pd.DataFrame(self.games)

        stats = {}

        # Overall statistics
        stats['total_games'] = len(df)
        stats['wins'] = len(df[df['outcome'] == 'win'])
        stats['losses'] = len(df[df['outcome'] == 'loss'])
        stats['draws'] = len(df[df['outcome'] == 'draw'])
        stats['win_rate'] = (stats['wins'] / stats['total_games']) * 100

        # Color statistics
        white_games = df[df['my_color'] == 'white']
        black_games = df[df['my_color'] == 'black']

        stats['white_games'] = len(white_games)
        stats['white_wins'] = len(white_games[white_games['outcome'] == 'win'])
        stats['white_win_rate'] = (stats['white_wins'] / stats['white_games']) * 100 if stats['white_games'] > 0 else 0

        stats['black_games'] = len(black_games)
        stats['black_wins'] = len(black_games[black_games['outcome'] == 'win'])
        stats['black_win_rate'] = (stats['black_wins'] / stats['black_games']) * 100 if stats['black_games'] > 0 else 0

        # Rating statistics
        stats['current_rating'] = df['my_elo'].iloc[-1] if len(df) > 0 else 0
        stats['highest_rating'] = df['my_elo'].max()
        stats['lowest_rating'] = df['my_elo'].min()
        stats['avg_rating'] = df['my_elo'].mean()

        # Time control statistics
        stats['time_control_breakdown'] = df['time_category'].value_counts().to_dict()

        # Opening statistics
        stats['top_openings'] = df['opening'].value_counts().head(10).to_dict()

        # Termination statistics
        stats['termination_breakdown'] = df['termination'].value_counts().to_dict()

        return stats, df

    def create_visualizations(self, df, output_dir='charts'):
        """Create performance-focused visualizations"""
        Path(output_dir).mkdir(exist_ok=True)

        print(f"Creating visualizations in {output_dir}/...")

        # 1. Rating progression over time
        self.plot_rating_progression(df, output_dir)

        # 2. Win rate by color
        self.plot_winrate_by_color(df, output_dir)

        # 3. Performance by time control
        self.plot_performance_by_time_control(df, output_dir)

        # 4. Top 10 openings performance
        self.plot_opening_performance(df, output_dir)

        # 5. Win/Loss/Draw distribution
        self.plot_outcome_distribution(df, output_dir)

        # 6. Rating change distribution
        self.plot_rating_change_distribution(df, output_dir)

        # 7. Performance by opponent rating difference
        self.plot_performance_vs_rating_diff(df, output_dir)

        # 8. Monthly activity and performance
        self.plot_monthly_performance(df, output_dir)

        # 9. Termination type analysis
        self.plot_termination_analysis(df, output_dir)

        # 10. Rolling win rate (last 100 games)
        self.plot_rolling_winrate(df, output_dir)

        print("All visualizations created!")

    def plot_rating_progression(self, df, output_dir):
        """Plot rating progression over time"""
        plt.figure(figsize=(14, 6))

        df_sorted = df.sort_values('datetime')
        dates = df_sorted['datetime']
        ratings = df_sorted['my_elo']

        plt.plot(dates, ratings, linewidth=1.5, alpha=0.7, color='#2E86AB')

        # Add trend line
        z = np.polyfit(range(len(ratings)), ratings, 1)
        p = np.poly1d(z)
        plt.plot(dates, p(range(len(ratings))), "--", color='#A23B72', linewidth=2, label=f'Trend (slope: {z[0]:.2f})')

        # Add horizontal line for current rating
        current_rating = ratings.iloc[-1]
        plt.axhline(y=current_rating, color='#F18F01', linestyle='--', alpha=0.5, label=f'Current: {current_rating}')

        plt.title('Rating Progression Over Time', fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Rating', fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/rating_progression.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_winrate_by_color(self, df, output_dir):
        """Plot win rate comparison by color"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        colors = ['white', 'black']
        color_palette = {'win': '#06A77D', 'loss': '#D62828', 'draw': '#F77F00'}

        for idx, color in enumerate(colors):
            color_df = df[df['my_color'] == color]
            outcomes = color_df['outcome'].value_counts()

            wedges, texts, autotexts = axes[idx].pie(
                outcomes.values,
                labels=outcomes.index,
                autopct='%1.1f%%',
                colors=[color_palette.get(x, '#999999') for x in outcomes.index],
                startangle=90
            )

            # Make percentage text bold
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(10)

            total_games = len(color_df)
            wins = len(color_df[color_df['outcome'] == 'win'])
            win_rate = (wins / total_games * 100) if total_games > 0 else 0

            axes[idx].set_title(f'As {color.capitalize()}\n{total_games} games | Win Rate: {win_rate:.1f}%',
                              fontsize=12, fontweight='bold')

        plt.suptitle('Performance by Color', fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/winrate_by_color.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_performance_by_time_control(self, df, output_dir):
        """Plot performance by time control"""
        plt.figure(figsize=(12, 6))

        time_controls = ['bullet', 'blitz', 'rapid', 'classical']
        tc_data = []

        for tc in time_controls:
            tc_df = df[df['time_category'] == tc]
            if len(tc_df) > 0:
                wins = len(tc_df[tc_df['outcome'] == 'win'])
                total = len(tc_df)
                win_rate = (wins / total * 100)
                tc_data.append({
                    'time_control': tc.capitalize(),
                    'win_rate': win_rate,
                    'games': total
                })

        tc_df_plot = pd.DataFrame(tc_data)

        if len(tc_df_plot) > 0:
            x = range(len(tc_df_plot))

            bars = plt.bar(x, tc_df_plot['win_rate'], color=['#06A77D', '#2E86AB', '#A23B72', '#F18F01'])

            # Add game count labels on bars
            for i, (bar, games) in enumerate(zip(bars, tc_df_plot['games'])):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{games} games',
                        ha='center', va='bottom', fontsize=9)

            plt.xticks(x, tc_df_plot['time_control'])
            plt.ylabel('Win Rate (%)', fontsize=12)
            plt.xlabel('Time Control', fontsize=12)
            plt.title('Win Rate by Time Control', fontsize=16, fontweight='bold')
            plt.ylim(0, max(tc_df_plot['win_rate']) * 1.2)
            plt.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{output_dir}/performance_by_time_control.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_opening_performance(self, df, output_dir):
        """Plot performance for top 10 most played openings"""
        plt.figure(figsize=(14, 8))

        # Get top 10 most played openings
        top_openings = df['opening'].value_counts().head(10).index

        opening_data = []
        for opening in top_openings:
            opening_df = df[df['opening'] == opening]
            wins = len(opening_df[opening_df['outcome'] == 'win'])
            losses = len(opening_df[opening_df['outcome'] == 'loss'])
            draws = len(opening_df[opening_df['outcome'] == 'draw'])
            total = len(opening_df)
            win_rate = (wins / total * 100)

            # Shorten opening name if too long
            short_name = opening if len(opening) <= 40 else opening[:37] + '...'

            opening_data.append({
                'opening': short_name,
                'win_rate': win_rate,
                'games': total,
                'wins': wins,
                'losses': losses,
                'draws': draws
            })

        opening_df_plot = pd.DataFrame(opening_data)
        opening_df_plot = opening_df_plot.sort_values('win_rate', ascending=True)

        # Create horizontal bar chart
        y_pos = range(len(opening_df_plot))

        # Color bars based on win rate
        colors = ['#06A77D' if wr >= 50 else '#D62828' for wr in opening_df_plot['win_rate']]

        bars = plt.barh(y_pos, opening_df_plot['win_rate'], color=colors, alpha=0.8)

        # Add game count labels
        for i, (bar, row) in enumerate(zip(bars, opening_df_plot.itertuples())):
            width = bar.get_width()
            plt.text(width + 1, bar.get_y() + bar.get_height()/2.,
                    f'{row.games} games ({row.wins}W-{row.losses}L-{row.draws}D)',
                    ha='left', va='center', fontsize=8)

        plt.yticks(y_pos, opening_df_plot['opening'], fontsize=9)
        plt.xlabel('Win Rate (%)', fontsize=12)
        plt.title('Top 10 Most Played Openings - Performance Analysis', fontsize=16, fontweight='bold')
        plt.axvline(x=50, color='gray', linestyle='--', alpha=0.5, label='50% baseline')
        plt.legend()
        plt.grid(axis='x', alpha=0.3)
        plt.xlim(0, max(opening_df_plot['win_rate']) * 1.3)

        plt.tight_layout()
        plt.savefig(f'{output_dir}/opening_performance.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_outcome_distribution(self, df, output_dir):
        """Plot overall outcome distribution"""
        plt.figure(figsize=(10, 6))

        outcomes = df['outcome'].value_counts()
        colors = {'win': '#06A77D', 'loss': '#D62828', 'draw': '#F77F00'}

        wedges, texts, autotexts = plt.pie(
            outcomes.values,
            labels=[f'{x.capitalize()}s' for x in outcomes.index],
            autopct='%1.1f%%',
            colors=[colors.get(x, '#999999') for x in outcomes.index],
            startangle=90,
            textprops={'fontsize': 12}
        )

        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(14)

        for text in texts:
            text.set_fontweight('bold')

        total = len(df)
        wins = outcomes.get('win', 0)
        losses = outcomes.get('loss', 0)
        draws = outcomes.get('draw', 0)

        plt.title(f'Overall Game Outcomes\n{total} Total Games | {wins}W - {losses}L - {draws}D',
                 fontsize=16, fontweight='bold')

        plt.tight_layout()
        plt.savefig(f'{output_dir}/outcome_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_rating_change_distribution(self, df, output_dir):
        """Plot distribution of rating changes"""
        plt.figure(figsize=(12, 6))

        rating_diffs = df['rating_diff'].dropna()

        # Create histogram
        plt.hist(rating_diffs, bins=50, color='#2E86AB', alpha=0.7, edgecolor='black')

        # Add vertical line at 0
        plt.axvline(x=0, color='red', linestyle='--', linewidth=2, label='No change')

        # Add mean line
        mean_diff = rating_diffs.mean()
        plt.axvline(x=mean_diff, color='green', linestyle='--', linewidth=2, label=f'Average: {mean_diff:.2f}')

        plt.xlabel('Rating Change', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        plt.title('Distribution of Rating Changes per Game', fontsize=16, fontweight='bold')
        plt.legend()
        plt.grid(alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{output_dir}/rating_change_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_performance_vs_rating_diff(self, df, output_dir):
        """Plot performance vs opponent rating difference"""
        plt.figure(figsize=(12, 6))

        # Calculate rating difference (my_elo - opp_elo)
        df['rating_difference'] = df['my_elo'] - df['opp_elo']

        # Create bins for rating differences
        bins = [-np.inf, -200, -100, -50, 0, 50, 100, 200, np.inf]
        labels = ['<-200', '-200 to -100', '-100 to -50', '-50 to 0', '0 to 50', '50 to 100', '100 to 200', '>200']

        df['rating_bin'] = pd.cut(df['rating_difference'], bins=bins, labels=labels)

        bin_data = []
        for label in labels:
            bin_df = df[df['rating_bin'] == label]
            if len(bin_df) > 0:
                wins = len(bin_df[bin_df['outcome'] == 'win'])
                total = len(bin_df)
                win_rate = (wins / total * 100)
                bin_data.append({
                    'bin': label,
                    'win_rate': win_rate,
                    'games': total
                })

        if len(bin_data) > 0:
            bin_df_plot = pd.DataFrame(bin_data)

            x = range(len(bin_df_plot))
            bars = plt.bar(x, bin_df_plot['win_rate'], color='#A23B72', alpha=0.8)

            # Add game count labels
            for bar, games in zip(bars, bin_df_plot['games']):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{games}',
                        ha='center', va='bottom', fontsize=9)

            plt.xticks(x, bin_df_plot['bin'], rotation=45, ha='right')
            plt.ylabel('Win Rate (%)', fontsize=12)
            plt.xlabel('Rating Difference (My Rating - Opponent Rating)', fontsize=12)
            plt.title('Performance vs Opponent Rating Difference', fontsize=16, fontweight='bold')
            plt.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% baseline')
            plt.legend()
            plt.grid(axis='y', alpha=0.3)
            plt.ylim(0, 100)

        plt.tight_layout()
        plt.savefig(f'{output_dir}/performance_vs_rating_diff.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_monthly_performance(self, df, output_dir):
        """Plot monthly activity and performance"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

        # Create year-month column
        df['year_month'] = df['datetime'].dt.to_period('M')

        # Monthly game count
        monthly_games = df.groupby('year_month').size()

        ax1.bar(range(len(monthly_games)), monthly_games.values, color='#2E86AB', alpha=0.8)
        ax1.set_xticks(range(len(monthly_games)))
        ax1.set_xticklabels([str(x) for x in monthly_games.index], rotation=45, ha='right')
        ax1.set_ylabel('Games Played', fontsize=12)
        ax1.set_title('Monthly Activity', fontsize=14, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)

        # Monthly win rate
        monthly_winrate = []
        months = []
        for month in monthly_games.index:
            month_df = df[df['year_month'] == month]
            wins = len(month_df[month_df['outcome'] == 'win'])
            total = len(month_df)
            win_rate = (wins / total * 100) if total > 0 else 0
            monthly_winrate.append(win_rate)
            months.append(str(month))

        ax2.plot(range(len(monthly_winrate)), monthly_winrate, marker='o', linewidth=2, markersize=6, color='#06A77D')
        ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% baseline')
        ax2.set_xticks(range(len(months)))
        ax2.set_xticklabels(months, rotation=45, ha='right')
        ax2.set_ylabel('Win Rate (%)', fontsize=12)
        ax2.set_xlabel('Month', fontsize=12)
        ax2.set_title('Monthly Win Rate', fontsize=14, fontweight='bold')
        ax2.legend()
        ax2.grid(alpha=0.3)
        ax2.set_ylim(0, 100)

        plt.tight_layout()
        plt.savefig(f'{output_dir}/monthly_performance.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_termination_analysis(self, df, output_dir):
        """Plot termination type analysis"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        # Overall termination distribution
        terminations = df['termination'].value_counts()

        wedges, texts, autotexts = ax1.pie(
            terminations.values,
            labels=terminations.index,
            autopct='%1.1f%%',
            startangle=90
        )

        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')

        ax1.set_title('Game Termination Types', fontsize=14, fontweight='bold')

        # Win rate by termination type
        term_data = []
        for term in terminations.index:
            term_df = df[df['termination'] == term]
            wins = len(term_df[term_df['outcome'] == 'win'])
            total = len(term_df)
            win_rate = (wins / total * 100) if total > 0 else 0
            term_data.append({
                'termination': term,
                'win_rate': win_rate,
                'games': total
            })

        term_df_plot = pd.DataFrame(term_data)
        term_df_plot = term_df_plot.sort_values('win_rate', ascending=True)

        y_pos = range(len(term_df_plot))
        bars = ax2.barh(y_pos, term_df_plot['win_rate'], color='#F18F01', alpha=0.8)

        # Add game count labels
        for bar, games in zip(bars, term_df_plot['games']):
            width = bar.get_width()
            ax2.text(width + 1, bar.get_y() + bar.get_height()/2.,
                    f'{games} games',
                    ha='left', va='center', fontsize=9)

        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(term_df_plot['termination'])
        ax2.set_xlabel('Win Rate (%)', fontsize=12)
        ax2.set_title('Win Rate by Termination Type', fontsize=14, fontweight='bold')
        ax2.axvline(x=50, color='gray', linestyle='--', alpha=0.5)
        ax2.grid(axis='x', alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{output_dir}/termination_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_rolling_winrate(self, df, output_dir):
        """Plot rolling win rate (last 100 games)"""
        plt.figure(figsize=(14, 6))

        df_sorted = df.sort_values('datetime')

        # Calculate rolling win rate
        window = 100
        df_sorted['outcome_numeric'] = df_sorted['outcome'].map({'win': 1, 'loss': 0, 'draw': 0.5})
        rolling_wr = df_sorted['outcome_numeric'].rolling(window=window, min_periods=1).mean() * 100

        plt.plot(range(len(rolling_wr)), rolling_wr, linewidth=2, color='#06A77D', label=f'{window}-game rolling avg')
        plt.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% baseline')

        # Add current rolling win rate
        current_wr = rolling_wr.iloc[-1]
        plt.axhline(y=current_wr, color='#D62828', linestyle='--', alpha=0.5, label=f'Current: {current_wr:.1f}%')

        plt.xlabel('Game Number', fontsize=12)
        plt.ylabel('Win Rate (%)', fontsize=12)
        plt.title(f'Rolling Win Rate (Last {window} Games)', fontsize=16, fontweight='bold')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.ylim(0, 100)

        plt.tight_layout()
        plt.savefig(f'{output_dir}/rolling_winrate.png', dpi=300, bbox_inches='tight')
        plt.close()


def main():
    # Initialize analyzer
    analyzer = ChessAnalyzer('lichess_Cassiny_2025-11-29.pgn')

    # Parse PGN file
    games = analyzer.parse_pgn()

    # Get statistics
    stats, df = analyzer.get_statistics()

    # Print key statistics
    print("\n" + "="*60)
    print("CHESS PERFORMANCE ANALYSIS - KEY INSIGHTS")
    print("="*60)
    print(f"\nTotal Games: {stats['total_games']}")
    print(f"Record: {stats['wins']}W - {stats['losses']}L - {stats['draws']}D")
    print(f"Overall Win Rate: {stats['win_rate']:.2f}%")
    print(f"\nAs White: {stats['white_games']} games | Win Rate: {stats['white_win_rate']:.2f}%")
    print(f"As Black: {stats['black_games']} games | Win Rate: {stats['black_win_rate']:.2f}%")
    print(f"\nCurrent Rating: {stats['current_rating']}")
    print(f"Highest Rating: {stats['highest_rating']}")
    print(f"Lowest Rating: {stats['lowest_rating']}")
    print(f"Average Rating: {stats['avg_rating']:.0f}")
    print("\n" + "="*60)

    # Create visualizations
    analyzer.create_visualizations(df)

    # Save statistics to file
    with open('stats_summary.txt', 'w') as f:
        f.write("CHESS PERFORMANCE ANALYSIS - DETAILED STATISTICS\n")
        f.write("="*60 + "\n\n")
        f.write(f"Total Games: {stats['total_games']}\n")
        f.write(f"Record: {stats['wins']}W - {stats['losses']}L - {stats['draws']}D\n")
        f.write(f"Overall Win Rate: {stats['win_rate']:.2f}%\n\n")
        f.write(f"As White: {stats['white_games']} games | Win Rate: {stats['white_win_rate']:.2f}%\n")
        f.write(f"As Black: {stats['black_games']} games | Win Rate: {stats['black_win_rate']:.2f}%\n\n")
        f.write(f"Current Rating: {stats['current_rating']}\n")
        f.write(f"Highest Rating: {stats['highest_rating']}\n")
        f.write(f"Lowest Rating: {stats['lowest_rating']}\n")
        f.write(f"Average Rating: {stats['avg_rating']:.0f}\n\n")
        f.write("Time Control Breakdown:\n")
        for tc, count in stats['time_control_breakdown'].items():
            f.write(f"  {tc}: {count} games\n")
        f.write("\nTop 10 Openings:\n")
        for opening, count in stats['top_openings'].items():
            f.write(f"  {opening}: {count} games\n")

    print("\nAnalysis complete! Check the 'charts' folder for visualizations.")
    print("Statistics saved to 'stats_summary.txt'")


if __name__ == '__main__':
    main()

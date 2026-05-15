import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface ChartProps {
  data: any;
}

const ChartComponent: React.FC<ChartProps> = ({ data }) => {
  if (!data) return null;

  const FRAME_WIDTH = 378; // ~10cm at 96dpi
  const FRAME_HEIGHT = 378; // ~10cm at 96dpi

  // Hard-lock chart domain so Y-axis never auto-expands between renders.
  const yMax = 140;
  const yStep = 20;

  const options = {
    responsive: false,
    maintainAspectRatio: false,
    animation: false,
    devicePixelRatio: 1,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: '#F8FAFC',
          font: { family: 'Inter', weight: 'bold' }
        }
      },
      title: {
        display: true,
        text: data.title || 'Groundwater Trends',
        color: '#F8FAFC',
        font: { size: 18, family: 'Playfair Display', weight: 'bold' }
      },
      tooltip: {
        backgroundColor: '#121826',
        titleFont: { family: 'Inter' },
        bodyFont: { family: 'Inter' },
        borderWidth: 1,
        borderColor: '#1E293B',
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        min: 0,
        max: yMax,
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: {
          color: '#94A3B8',
          stepSize: yStep,
        }
      },
      x: {
        grid: { display: false },
        ticks: { color: '#94A3B8' }
      }
    }
  };

  // Convert custom API data format to Chart.js format
  const chartData = {
    labels: data.datasets[0].labels || data.datasets[0].data.map((d: any) => d.x),
    datasets: data.datasets.map((ds: any) => ({
      ...ds,
      data: ds.labels ? ds.data : ds.data.map((d: any) => d.y),
      tension: 0.4,
      pointRadius: 6,
      pointHoverRadius: 8,
      borderWidth: 3,
      borderColor: ds.borderColor || '#3B82F6',
      backgroundColor: ds.backgroundColor || 'rgba(59, 130, 246, 0.1)',
      maxBarThickness: 48,
      categoryPercentage: 0.7,
      barPercentage: 0.85,
    }))
  };

  return (
    <div className="w-[430px] max-w-[430px] mx-auto glass-card p-4 md:p-5">
      <div
        className="relative mx-auto overflow-hidden rounded-xl chart-fixed-shell"
      >
        {data.type === 'line' ? (
          <Line width={FRAME_WIDTH} height={FRAME_HEIGHT} options={options as any} data={chartData} style={{ width: `${FRAME_WIDTH}px`, height: `${FRAME_HEIGHT}px` }} />
        ) : (
          <Bar width={FRAME_WIDTH} height={FRAME_HEIGHT} options={options as any} data={chartData} style={{ width: `${FRAME_WIDTH}px`, height: `${FRAME_HEIGHT}px` }} />
        )}
      </div>
      <div className="mt-4 text-center">
        <p className="text-[10px] font-bold text-text-muted uppercase tracking-[0.2em]">{data.source || 'INGRES Predictive Data Source'}</p>
      </div>
    </div>
  );
};

export default ChartComponent;

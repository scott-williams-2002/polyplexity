import React from 'react';
import { ApprovedMarket } from '../types';
import PolymarketChart from './PolymarketGraph';

interface MarketChartsContainerProps {
  markets: ApprovedMarket[];
}

export const MarketChartsContainer: React.FC<MarketChartsContainerProps> = ({ markets }) => {
  if (markets.length === 0) {
    return null;
  }

  return (
    <div className="mt-8 space-y-6">
      {markets.map((market, index) => (
        <div key={`${market.slug}-${index}`} className="w-full max-w-full overflow-hidden">
          <PolymarketChart market={market} />
        </div>
      ))}
    </div>
  );
};

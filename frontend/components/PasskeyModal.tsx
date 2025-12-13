import React, { useState } from 'react';
import { setApiKey } from '@/lib/auth';

interface PasskeyModalProps {
  onSave: () => void;
}

export const PasskeyModal: React.FC<PasskeyModalProps> = ({ onSave }) => {
  const [passkey, setPasskey] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!passkey.trim()) {
      setError('Please enter a passkey');
      return;
    }

    try {
      setApiKey(passkey.trim());
      setError(null);
      onSave();
    } catch (err) {
      setError('Failed to save passkey. Please try again.');
      console.error('Error saving passkey:', err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-background border border-border rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <h2 className="text-2xl font-bold mb-2">Enter Passkey</h2>
        <p className="text-sm text-muted-foreground mb-6">
          A passkey is required to authenticate with the API. Please enter your passkey to continue.
        </p>
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="passkey" className="block text-sm font-medium mb-2">
              Passkey
            </label>
            <input
              id="passkey"
              type="password"
              value={passkey}
              onChange={(e) => {
                setPasskey(e.target.value);
                setError(null);
              }}
              placeholder="Enter passkey..."
              className="w-full px-4 py-2 bg-muted/30 border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50 transition-all"
              autoFocus
            />
            {error && (
              <p className="mt-2 text-sm text-destructive">{error}</p>
            )}
          </div>
          
          <button
            type="submit"
            className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors shadow-md"
          >
            Save
          </button>
        </form>
      </div>
    </div>
  );
};


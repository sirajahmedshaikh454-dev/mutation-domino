import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import { SearchForm } from '../src/components/SearchForm';

describe('SearchForm', () => {
  it('navigates with a valid accession', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <SearchForm />
      </MemoryRouter>,
    );
    const input = screen.getByLabelText('UniProt accession');
    await user.type(input, 'p69905');
    await user.click(screen.getByRole('button', { name: /load protein/i }));
    expect((input as HTMLInputElement).value).toBe('p69905');
  });

  it('shows an error for an invalid accession', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <SearchForm />
      </MemoryRouter>,
    );
    const input = screen.getByLabelText('UniProt accession');
    await user.type(input, 'x');
    await user.click(screen.getByRole('button', { name: /load protein/i }));
    expect(screen.getByRole('alert')).toBeTruthy();
  });
});
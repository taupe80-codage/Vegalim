import { describe, expect, it } from 'vitest';
import { checkPhotoForm, PHOTO_MAX_BYTES } from '../photoForm';

const jpeg = (size = 1000) => ({ type: 'image/jpeg', size });

describe('checkPhotoForm', () => {
  it('accepte une photo complète', () => {
    expect(checkPhotoForm({ file: jpeg(), author: 'Léa', consent: true })).toBe('');
  });
  it("signale ce qui manque, dans l'ordre du formulaire", () => {
    expect(checkPhotoForm({ file: null, author: 'Léa', consent: true })).toMatch(/Choisissez/);
    expect(checkPhotoForm({ file: { type: 'image/gif', size: 10 }, author: 'Léa', consent: true })).toMatch(/Format/);
    expect(checkPhotoForm({ file: jpeg(PHOTO_MAX_BYTES + 1), author: 'Léa', consent: true })).toMatch(/8 Mo/);
    expect(checkPhotoForm({ file: jpeg(), author: ' L ', consent: true })).toMatch(/pseudo/);
    expect(checkPhotoForm({ file: jpeg(), author: 'Léa', consent: false })).toMatch(/Cochez/);
  });
});

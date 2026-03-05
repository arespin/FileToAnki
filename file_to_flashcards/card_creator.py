"""
Anki card creation module.
Creates notes directly in the Anki collection.
"""

from aqt import mw
from anki.notes import Note


def get_deck_names():
    """Return list of all deck names in the collection."""
    if not mw.col:
        return ["Default"]
    return sorted(mw.col.decks.all_names())


def get_basic_model():
    """Get or create a Basic note type."""
    model = mw.col.models.by_name("Basic")
    if model:
        return model

    # Try other common names
    for name in ["basic", "Basis", "Einfach"]:
        model = mw.col.models.by_name(name)
        if model:
            return model

    # Create a basic model if none exists
    model = mw.col.models.new("Basic")
    front = mw.col.models.new_field("Front")
    back = mw.col.models.new_field("Back")
    mw.col.models.add_field(model, front)
    mw.col.models.add_field(model, back)

    tmpl = mw.col.models.new_template("Card 1")
    tmpl["qfmt"] = "{{Front}}"
    tmpl["afmt"] = "{{FrontSide}}<hr id=answer>{{Back}}"
    mw.col.models.add_template(model, tmpl)

    mw.col.models.add(model)
    return model


def create_cards(flashcards, deck_name):
    """
    Create Anki notes from flashcards.

    Args:
        flashcards: List of dicts with 'front' and 'back' keys
        deck_name: Name of the deck to add cards to

    Returns:
        Number of cards successfully created
    """
    if not mw.col:
        raise Exception("No collection open")

    # Get or create deck
    deck_id = mw.col.decks.id(deck_name)

    # Get note type
    model = get_basic_model()
    if not model:
        raise Exception("Could not find or create Basic note type")

    # Set the deck for new cards
    model['did'] = deck_id
    mw.col.models.save(model)

    created = 0
    for card in flashcards:
        front = card.get('front', '').strip()
        back = card.get('back', '').strip()

        if not front or not back:
            continue

        note = Note(mw.col, model)
        note.fields[0] = front
        note.fields[1] = back

        # Add the note - compatible with different Anki versions
        try:
            # Anki 2.1.45+
            mw.col.add_note(note, deck_id)
        except TypeError:
            # Older Anki versions
            note.model()['did'] = deck_id
            mw.col.addNote(note)

        created += 1

    # Save changes
    mw.col.save()

    # Refresh the main window to show new cards
    mw.reset()

    return created

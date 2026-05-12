import pickle

def main() -> None:
    with open("./data/ocr_processed.pkl", "rb") as f:
        result = pickle.load(f)
        print(len(result))

if __name__ == '__main__':
    main()
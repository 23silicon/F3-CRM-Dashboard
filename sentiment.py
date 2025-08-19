from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as nnf

model_name = tokenizer = model = None
def init():
    global model_name, tokenizer, model
    model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    


def get(text):
    positivekw = [
    "let's talk", "let us talk", "schedule", "meeting", "interested",
    "love to", "available", "happy to", "looking forward", "would like", "chat", "meeting"
]

    negativekw = [
        "unfortunately", "not moving forward", "reject", "not be moving forward",
        "not interested", "not a fit", "decline", "pass on", "did not qualify", "disappointing"
    ]

    t = text.lower()
    
    poscount = negcount = 0
    if any(kw in t for kw in positivekw):
        poscount += 1
    if any(kw in t for kw in negativekw):
        negcount += 1

    if poscount > negcount:
        return "positive"
    elif negcount > poscount:
        return "negative"
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length = 512, padding="max_length")
    outputs = model(**inputs)
    probs = nnf.softmax(outputs.logits, dim=1)
    positive_score = probs[0][1].item()
    negative_score = probs[0][0].item()
    #print(positive_score)
    #print(negative_score)
    return "positive" if positive_score > negative_score else "negative"

if __name__ == '__main__':
    for i in range(10):
        a = input()
        print(get(a))
import argparse

def parse_search_input():

    keys = ["journals", "publications", "year"]

    s = "authors(journals='https://cos.io/top/', publications='https://www.ncbi.nlm.nih.gov/', year=2016)"
    # s = "authors(journals='https://cos.io/top/', publications='https://www.ncbi.nlm.nih.gov/')"
    # s = "authors(journals='https://cos.io/top/', publications=)"

    index = s.find("(")
    if index != -1:
        what_criteria = s[0:index]

        sub_s = s[index+1 : -1]
        parser = argparse.ArgumentParser()

        for key in keys:
            sub_s = sub_s.replace(key + "=", "--{0} ".format(key))

            parser.add_argument("--{0}".format(key), default="")

        options = parser.parse_args(sub_s.split())

        return (what_criteria, options)

    else:

        return None


if __name__ == "__main__":
    pass



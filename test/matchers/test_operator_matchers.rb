require File.dirname(__FILE__) + "/../test_helper.rb"

describe "Equals Operator: ==" do
  describe "obj.should == other_object" do
    it "passes if obj == other_object evals to true" do
      1.should == 1
    end

    it "fails if obj == other_object evals to false" do
      lambda {1.should == 2}.should raise_error
    end
  end

  describe "obj.should_not == other_object" do
    it "fails if obj == other_object evals to true" do
      lambda {1.should_not == 1}.should raise_error
    end

    it "passes if obj == other_object evals to false" do
      1.should_not == 2
    end
  end
end

describe "Matches Operator: =~" do
  describe "string.should =~ regex" do

    it "passes if string =~ regex evals to true equiv." do
      "abc".should =~ /a/
    end

    it "fails if string =~ regex evals to false equiv." do
      lambda {"abc".should =~ /d/}.should raise_error
    end

  end

  describe "string.should_not =~ regex" do

    it "passes if string =~ regex evals to false equiv." do
      lambda {"abc".should_not =~ /a/}.should raise_error
    end

    it "fails if string =~ regex evals to false equiv." do
      "abc".should_not =~ /d/
    end

  end
end